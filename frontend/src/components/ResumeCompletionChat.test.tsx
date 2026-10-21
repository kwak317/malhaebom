import {act} from 'react';
import {createRoot,type Root} from 'react-dom/client';
import {renderToStaticMarkup} from 'react-dom/server';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
const polishMock=vi.hoisted(()=>vi.fn());
vi.mock('../api/resumeAssistance',async(importOriginal)=>({...await importOriginal<typeof import('../api/resumeAssistance')>(),polishResumeInformation:polishMock}));
import {ResumeCompletionChat} from './ResumeCompletionChat';
import {ResumeDraftChat,type ResumeDraftMaterials} from './ResumeDraftChat';
import {buildResumeDocument} from '../resume/document';
(globalThis as typeof globalThis & {IS_REACT_ACT_ENVIRONMENT:boolean}).IS_REACT_ACT_ENVIRONMENT=true;
describe('이력서 일괄 입력 폼',()=>{
 let root:Root;let container:HTMLDivElement;
 beforeEach(()=>{polishMock.mockReset();container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);});
 afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks();});
 const fill=async(field:string,value:string)=>{const input=container.querySelector<HTMLInputElement|HTMLTextAreaElement>(`#resume-completion-${field}`)!;await act(async()=>{Object.getOwnPropertyDescriptor(input instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));});};
 const submit=async()=>{await act(async()=>container.querySelector('form')!.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));};
 it('18개 항목을 한 번에 보여주고 기존 자료를 수정한 값만 초안과 PDF 모델에 반영한다',async()=>{
  const complete=vi.fn();const materials:ResumeDraftMaterials={resumeProfile:{facts:[{category:'role',value:'기존 직무',keyword:null},{category:'technology',value:'기존 기술',keyword:null}]}};
  await act(async()=>root.render(<ResumeCompletionChat onComplete={complete} onCancel={()=>{}} materials={materials}/>));
  expect(container.querySelectorAll('.resume-completion-field input,.resume-completion-field textarea')).toHaveLength(18);
  expect(container.querySelector<HTMLInputElement>('#resume-completion-role')!.value).toBe('');
  await fill('name','김테스트');await fill('role','변경 직무');await fill('technology','변경 기술');await fill('projectRole','API 구현');
  expect(complete).not.toHaveBeenCalled();await submit();expect(complete).toHaveBeenCalledTimes(1);
  const completed=complete.mock.calls[0][0];
  for(const layout of ['project','career'] as const){const html=renderToStaticMarkup(<ResumeDraftChat layout={layout} materials={materials} completion={completed}/>);expect(html).toContain('변경 직무');expect(html).not.toContain('기존 직무');expect(html).not.toContain('기존 기술');const pdf=JSON.stringify(buildResumeDocument(layout,materials,completed));expect(pdf).toContain('변경 기술');expect(pdf).not.toContain('기존 기술');}
 });
 it('모두 채운 상태도 수정할 수 있고 비운 기존 항목을 다시 추가하지 않는다',async()=>{
  const complete=vi.fn();await act(async()=>root.render(<ResumeCompletionChat onComplete={complete} onCancel={()=>{}} initial={{name:'기존 이름',email:'old@example.test',role:'기존 직무'}}/>));
  await fill('name','새 이름');await fill('role','');await submit();expect(complete.mock.calls[0][0]).toMatchObject({name:'새 이름',email:'old@example.test',role:''});
 });
 it('기존 사진을 재보완에 유지하고 삭제하면 초안과 PDF 모델에서도 제거한다',async()=>{
  const complete=vi.fn();const photo='data:image/png;base64,example';
  await act(async()=>root.render(<ResumeCompletionChat onComplete={complete} onCancel={()=>{}} initial={{photoDataUrl:photo}}/>));
  expect(container.querySelector('img')?.getAttribute('src')).toBe(photo);
  await submit();expect(complete.mock.calls[0][0].photoDataUrl).toBe(photo);
  await act(async()=>Array.from(container.querySelectorAll('button')).find(button=>button.textContent==='사진 삭제')!.click());
  expect(container.querySelector('img')).toBeNull();await submit();
  expect(buildResumeDocument('career',{},complete.mock.calls[1][0]).photoDataUrl).toBe('');
 });
 it('지원하지 않는 사진과 5MB 초과 파일을 거부한다',async()=>{
  await act(async()=>root.render(<ResumeCompletionChat onComplete={()=>{}} onCancel={()=>{}}/>));
  const input=container.querySelector<HTMLInputElement>('#resume-completion-photo')!;
  for(const file of [new File(['gif'],'photo.gif',{type:'image/gif'}),new File([new Uint8Array(5*1024*1024+1)],'large.png',{type:'image/png'})]){
   await act(async()=>{Object.defineProperty(input,'files',{configurable:true,value:[file]});input.dispatchEvent(new Event('change',{bubbles:true}));});
   expect(container.querySelector('[role=alert]')?.textContent).toContain('5MB');expect(container.querySelector('img')).toBeNull();
  }
 });
 it('사실 확인 답변 후 해당 항목만 재요청하고 이름과 사진은 유지한다',async()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true);
  polishMock.mockResolvedValueOnce({items:[{field:'technology',value:'Spring Boot로 API를 구현했습니다.',source_excerpt:'Spring Boot API'}],questions:[{field:'projectRole',question:'본인이 직접 구현한 기능은 무엇인가요?',source_excerpt:'팀 개발 참여'}]});
  polishMock.mockResolvedValueOnce({items:[{field:'projectRole',value:'상품 조회 API를 직접 구현했습니다.',source_excerpt:'상품 조회 API를 직접 구현했습니다.'}],questions:[]});
  await act(async()=>root.render(<ResumeCompletionChat onComplete={()=>{}} onCancel={()=>{}} initial={{name:'김테스트',photoDataUrl:'data:image/png;base64,test',technology:'Spring Boot API',projectRole:'팀 개발 참여'}}/>));
  const button=(label:string)=>Array.from(container.querySelectorAll('button')).find(node=>node.textContent===label)!;
  await act(async()=>button('이력서 문장 다듬기').click());
  expect(container.textContent).toContain('본인이 직접 구현한 기능');
  await act(async()=>{const input=container.querySelector<HTMLTextAreaElement>('#resume-fact-answer')!;Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')!.set!.call(input,'상품 조회 API를 직접 구현했습니다.');input.dispatchEvent(new Event('input',{bubbles:true}));});
  await act(async()=>button('답변 보내고 이 항목 다듬기').click());
  expect(Object.keys(polishMock.mock.calls[1][0])).toEqual(['projectRole']);
  expect(container.querySelector<HTMLInputElement>('#resume-completion-name')!.value).toBe('김테스트');
  expect(container.querySelector('img')?.getAttribute('src')).toBe('data:image/png;base64,test');
  expect(container.querySelector<HTMLTextAreaElement>('#resume-completion-projectRole')!.value).toBe('상품 조회 API를 직접 구현했습니다.');
 });
 it('AI 동의 취소 시 호출하지 않고 실패해도 입력을 유지한다',async()=>{
  const consent=vi.spyOn(window,'confirm').mockReturnValue(false);
  await act(async()=>root.render(<ResumeCompletionChat onComplete={()=>{}} onCancel={()=>{}} initial={{intro:'원래 소개'}}/>));
  const button=Array.from(container.querySelectorAll('button')).find(node=>node.textContent==='이력서 문장 다듬기')!;
  await act(async()=>button.click());expect(polishMock).not.toHaveBeenCalled();
  consent.mockReturnValue(true);polishMock.mockRejectedValue(new Error('출력 한도 오류'));
  await act(async()=>button.click());expect(container.querySelector<HTMLTextAreaElement>('#resume-completion-intro')!.value).toBe('원래 소개');expect(container.textContent).toContain('출력 한도 오류');
 });
 it('사실 확인 재요청 실패 후 건너뛰어도 제어 문구나 답변으로 원문을 덮지 않는다',async()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true);
  polishMock.mockResolvedValueOnce({items:[],questions:[{field:'projectRole',question:'직접 구현한 기능?',source_excerpt:'팀 개발 참여'}]}).mockRejectedValueOnce(new Error('일시적 오류'));
  const complete=vi.fn();await act(async()=>root.render(<ResumeCompletionChat onComplete={complete} onCancel={()=>{}} initial={{projectRole:'팀 개발 참여'}}/>));
  const button=(label:string)=>Array.from(container.querySelectorAll('button')).find(node=>node.textContent===label)!;
  await act(async()=>button('이력서 문장 다듬기').click());
  await act(async()=>{const input=container.querySelector<HTMLTextAreaElement>('#resume-fact-answer')!;Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')!.set!.call(input,'상품 조회 API 구현');input.dispatchEvent(new Event('input',{bubbles:true}));});
  await act(async()=>button('답변 보내고 이 항목 다듬기').click());
  expect(container.querySelector<HTMLTextAreaElement>('#resume-completion-projectRole')!.value).toBe('팀 개발 참여');
  await act(async()=>button('원문 유지하고 건너뛰기').click());await submit();
  expect(complete.mock.calls[0][0].projectRole).toBe('팀 개발 참여');
 });
 it('이메일과 URL을 검증하고 빈 선택 항목은 허용한다',async()=>{
  const complete=vi.fn();await act(async()=>root.render(<ResumeCompletionChat onComplete={complete} onCancel={()=>{}}/>));
  await fill('email','invalid');await submit();expect(complete).not.toHaveBeenCalled();expect(container.querySelector('[role="alert"]')?.textContent).toContain('이메일 형식');
  await fill('email','valid@example.test');await fill('github','javascript:alert(1)');await submit();expect(complete).not.toHaveBeenCalled();expect(container.querySelector('[role="alert"]')?.textContent).toContain('올바른 주소');
  await fill('github','');await submit();expect(complete).toHaveBeenCalledTimes(1);
 });
});

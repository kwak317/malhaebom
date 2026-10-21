// @vitest-environment node
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {describe,it,expect} from 'vitest';
import {PDFDocument} from 'pdf-lib';
import {buildResumeDocument} from './document';
import {createResumePdf} from './pdf';
import type {ResumeCompletion} from '../components/ResumeDraftChat';
const completion:ResumeCompletion={name:'김테스트',email:'resume@example.test',role:'백엔드 개발자',github:'https://github.com/example',portfolio:'https://example.test',intro:'사용자 요청을 안정적으로 처리하는 백엔드 개발자입니다.',career:'가상테크 · 개발 인턴 · 2026.01–2026.03',careerDetails:'로그인 API 구현과 통합 테스트를 담당했습니다.',technology:'Java 17 · Spring Boot · MySQL · JPA',project:'가상 쇼핑몰 · 2026.01–2026.03 · 4명',projectRole:'상품 조회 API와 페이지네이션을 구현했습니다.',problem:'동일한 상품 요청에서 반복 조회가 발생했습니다.',action:'조회 흐름을 분석하고 캐시를 적용했습니다.',result:'테스트 환경에서 반복 조회 감소를 확인했습니다.',outcome:'응답 시간은 별도로 측정하지 않았습니다.',repository:'https://github.com/example/shop',education:'가상대학교 컴퓨터공학 · 2026년 졸업',qualification:'정보처리기사 · 2026년'};
describe('이력서 PDF',()=>{
 for(const layout of ['project','career'] as const)it(`${layout} 내용과 한글 글꼴을 포함한 A4 PDF를 만든다`,async()=>{
  const document=buildResumeDocument(layout,{},completion);
  expect(document.sections[0].title).toBe(layout==='project'?'기술 스택':'경력 및 활동');
  expect(JSON.stringify(document)).not.toContain('확인 필요');
  expect(JSON.stringify(document)).toContain(completion.projectRole);
  const bytes=await createResumePdf(document,new Uint8Array(readFileSync('public/fonts/NanumGothic-Regular.ttf')));
  const pdf=await PDFDocument.load(bytes);
  expect(pdf.getPageCount()).toBe(1);expect(pdf.getPage(0).getWidth()).toBeCloseTo(595.28,1);
  if(process.env.RESUME_PDF_VERIFY_OUTPUT){mkdirSync(process.env.RESUME_PDF_VERIFY_OUTPUT,{recursive:true});writeFileSync(resolve(process.env.RESUME_PDF_VERIFY_OUTPUT,`${layout}.pdf`),bytes);}
 });
 it('긴 본문과 줄바꿈도 생략 없이 한 페이지에 맞춘다',async()=>{
  const document=buildResumeDocument('career',{},completion);
  document.sections[1].paragraphs=['긴 경험 설명입니다. '.repeat(150)+'\n마지막 확인 내용'];
  const bytes=await createResumePdf(document,new Uint8Array(readFileSync('public/fonts/NanumGothic-Regular.ttf')));
  expect((await PDFDocument.load(bytes)).getPageCount()).toBe(1);
  if(process.env.RESUME_PDF_VERIFY_OUTPUT)writeFileSync(resolve(process.env.RESUME_PDF_VERIFY_OUTPUT,'long.pdf'),bytes);
 });
 it('사진을 PDF에 삽입하고 두 양식 모두 한 페이지를 유지한다',async()=>{
  const photo=process.env.RESUME_PHOTO_VERIFY_INPUT?'data:image/png;base64,'+readFileSync(process.env.RESUME_PHOTO_VERIFY_INPUT).toString('base64'):'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==';
  for(const layout of ['project','career'] as const){
   const document=buildResumeDocument(layout,{}, {...completion,photoDataUrl:photo});
   const bytes=await createResumePdf(document,new Uint8Array(readFileSync('public/fonts/NanumGothic-Regular.ttf')));
   const pdf=await PDFDocument.load(bytes);expect(pdf.getPageCount()).toBe(1);
   expect(pdf.getPage(0).node.Resources()?.toString()).toContain('/XObject');
   if(process.env.RESUME_PDF_VERIFY_OUTPUT)writeFileSync(resolve(process.env.RESUME_PDF_VERIFY_OUTPUT,`photo-${layout}.pdf`),bytes);
  }
 });
 it('확인되지 않은 내용은 확인 필요로 남긴다',()=>{const document=buildResumeDocument('project');expect(document.name).toContain('확인 필요');expect(document.sections[1].paragraphs.join(' ')).toContain('개인 담당 기능 확인 필요');});
});

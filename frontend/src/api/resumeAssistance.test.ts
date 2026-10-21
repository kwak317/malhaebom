import {afterEach,describe,expect,it,vi} from 'vitest';
vi.mock('./supabaseAuth',()=>({supabase:()=>({auth:{getSession:async()=>({data:{session:{access_token:'synthetic-token'}}})}})}));
import {polishResumeInformation} from './resumeAssistance';
describe('경험 문장 전송 범위',()=>{
 afterEach(()=>vi.restoreAllMocks());
 it('이름 이메일 사진 경력 메타데이터를 제외하고 경험만 전송한다',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({items:[],questions:[]})));
  await polishResumeInformation({name:'가상 이름',email:'fake@example.test',photoDataUrl:'data:image/png;base64,test',career:'회사·기간',role:'개발자',action:'API 구현'});
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({consent:true,fields:{action:'API 구현'}});
 });
});

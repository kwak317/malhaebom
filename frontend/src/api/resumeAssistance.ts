import {API_BASE_URL} from '../config/apiBase';
import {supabase} from './supabaseAuth';
import type {ResumeCompletion} from '../components/ResumeDraftChat';
export const POLISH_FIELDS=['intro','careerDetails','technology','projectRole','problem','action','result','outcome'] as const;
export type PolishField=typeof POLISH_FIELDS[number];
export type AssistanceItem={field:keyof Omit<ResumeCompletion,'photoDataUrl'>;value:string;source_excerpt:string};
export type Clarification={field:PolishField;question:string;source_excerpt:string};
export type AssistanceResult={items:AssistanceItem[];questions?:Clarification[];omitted_items?:number;model:string;max_output_tokens:number};
async function call(path:string,body:FormData|string,signal?:AbortSignal):Promise<AssistanceResult>{
 const {data}=await supabase().auth.getSession();if(!data.session)throw new Error('로그인이 필요하거나 세션이 만료되었습니다.');
 if(signal?.aborted)throw new DOMException('Aborted','AbortError');
 const response=await fetch(`${API_BASE_URL}/api/resume/assist/${path}`,{method:'POST',headers:{Authorization:`Bearer ${data.session.access_token}`,...(typeof body==='string'?{'Content-Type':'application/json'}:{})},body,signal,cache:'no-store'});
 const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(typeof payload?.detail==='string'?payload.detail:'AI 결과를 가져오지 못했어요. 작성한 내용은 유지했습니다.');
 if(!payload||!Array.isArray(payload.items))throw new Error('AI 결과 형식을 확인하지 못했습니다.');
 return payload;
}
export function importResumeInformation(file:File,signal?:AbortSignal){const body=new FormData();body.append('file',file);body.append('consent','true');return call('import',body,signal);}
export function polishResumeInformation(values:ResumeCompletion,signal?:AbortSignal){
 const fields=Object.fromEntries(POLISH_FIELDS.filter(field=>values[field]?.trim()).map(field=>[field,values[field]!.trim()]));
 return call('polish',JSON.stringify({consent:true,fields}),signal);
}

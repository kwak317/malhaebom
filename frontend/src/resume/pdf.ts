import {PDFDocument,PageSizes,rgb} from 'pdf-lib';
import fontkit from '@pdf-lib/fontkit';
import type {ResumeDocument} from './document';

export async function createResumePdf(document:ResumeDocument,fontBytes:Uint8Array):Promise<Uint8Array>{
 const pdf=await PDFDocument.create();pdf.registerFontkit(fontkit);
 const font=await pdf.embedFont(fontBytes);const characters=new Set(font.getCharacterSet());
 const page=pdf.addPage(PageSizes.A4),margin=42,width=page.getWidth()-margin*2;
 const ink=rgb(.13,.17,.22),muted=rgb(.38,.43,.49),accent=rgb(.15,.30,.43),rule=rgb(.79,.83,.87);
 const photoWidth=80,photoHeight=104,photoX=margin+width-photoWidth,photoY=page.getHeight()-margin-photoHeight;
 page.drawRectangle({x:photoX,y:photoY,width:photoWidth,height:photoHeight,borderWidth:.6,borderColor:rule});
 if(document.photoDataUrl){
  const photo=/^data:image\/png;base64,/.test(document.photoDataUrl)?await pdf.embedPng(document.photoDataUrl):await pdf.embedJpg(document.photoDataUrl);
  const scale=Math.min((photoWidth-2)/photo.width,(photoHeight-2)/photo.height);
  const w=photo.width*scale,h=photo.height*scale;
  page.drawImage(photo,{x:photoX+(photoWidth-w)/2,y:photoY+(photoHeight-h)/2,width:w,height:h});
 }else page.drawText('증명사진',{x:photoX+22,y:photoY+48,font,size:9,color:muted});
 const clean=(value:string)=>Array.from(value.replace(/\t/g,'    ').replace(/[–—]/g,'-')).map(char=>char==='\n'||characters.has(char.codePointAt(0)!)?char:'?').join('');
 const wrap=(value:string,size:number,lineWidth=width)=>clean(value).split('\n').flatMap(paragraph=>{
  const lines:string[]=[];let line='';
  for(const char of Array.from(paragraph)){if(line&&font.widthOfTextAtSize(line+char,size)>lineWidth){lines.push(line);line='';}line+=char;}lines.push(line);return lines;
 });
 type Block={lines:string[];size:number;gap:number;color:ReturnType<typeof rgb>;divider?:boolean;label?:string};
 const blocksFor=(body:number):Block[]=>{
  const block=(value:string,size:number,gap:number,color=ink,divider=false):Block=>({lines:wrap(value,size),size,gap,color,divider});
  const projectLayout=document.layout==='project';
  const skills=document.sections.find(section=>section.title==='기술 스택');
  const order=projectLayout?['프로젝트 경험','경력 및 활동','교육 및 자격']:['경력 및 활동','프로젝트 경험','기술 스택','교육 및 자격'];
  const ordered=[...order.flatMap(title=>document.sections.filter(section=>section.title===title)),...document.sections.filter(section=>!order.includes(section.title)&&section.title!=='기술 스택')];
  const labels:Record<string,string>={'본인이 담당한 구현':'담당 구현','문제':'문제','행동':'해결 행동','결과':'확인한 결과','성과':'성과','저장소':'저장소'};
  const sections=ordered.flatMap(section=>[
   block(section.title==='프로젝트 경험'?(projectLayout?'대표 프로젝트':'주요 프로젝트'):section.title,body*1.25,body*.65,accent,true),
   ...section.paragraphs.map(paragraph=>{
    const match=section.title==='프로젝트 경험'&&projectLayout?paragraph.match(/^(본인이 담당한 구현|문제|행동|결과|성과|저장소):\s*([\s\S]*)$/):null;
    return match?{...block(match[2],body,body*.9),lines:wrap(match[2],body,width-86),label:labels[match[1]]}:block(paragraph,body,body*.45);
   }),
   block('',body,body*.25),
  ]);
  const header=[block(document.name,body*2.6,body*.5),block(document.role,body*1.25,body*.7,accent),...document.contacts.map(contact=>block(contact,body*.85,body*.2,muted))].map(item=>({...item,lines:item.lines.flatMap(line=>wrap(line,item.size,width-100))}));
  return [...header,block('',body,Math.max(body*.5,photoHeight+12-height(header)-body*1.4)),block(projectLayout?'핵심 소개':'경력 요약',body*1.25,body*.65,accent,true),block(document.intro,body,body*.6),
   ...(projectLayout&&skills?skills.paragraphs.map(paragraph=>block(`주요 기술: ${paragraph}`,body,body*.45)):[]),block('',body,body*.25),...sections];
 };
 const height=(blocks:Block[])=>blocks.reduce((sum,item)=>sum+item.lines.length*item.size*1.4+item.gap+(item.divider?7:0),0);
 const available=page.getHeight()-margin*2;
 let body=10.5,blocks=blocksFor(body);
 // Reflow every line before drawing so one page retains all user content.
 while(height(blocks)>available){body*=.97;blocks=blocksFor(body);}
 let y=page.getHeight()-margin;
 for(const block of blocks){
  if(block.divider){page.drawLine({start:{x:margin,y:y+2},end:{x:margin+width,y:y+2},thickness:.7,color:rule});y-=7;}
  if(block.label)page.drawText(block.label,{x:margin,y:y-block.size*1.15,font,size:block.size,color:accent});
  for(const line of block.lines){y-=block.size*1.4;page.drawText(line,{x:margin+(block.label?86:0),y:y+block.size*.25,font,size:block.size,color:block.color});}
  y-=block.gap;
 }
 return pdf.save();
}
export async function downloadResumePdf(document:ResumeDocument){
 const response=await fetch('/fonts/NanumGothic-Regular.ttf');if(!response.ok)throw new Error('한글 글꼴을 불러오지 못했습니다. 다시 시도해 주세요.');
 const bytes=await createResumePdf(document,new Uint8Array(await response.arrayBuffer()));
 const url=URL.createObjectURL(new Blob([new Uint8Array(bytes)],{type:'application/pdf'}));const anchor=window.document.createElement('a');anchor.href=url;anchor.download=`말해봄-${document.layout==='career'?'경력':'프로젝트'}-이력서.pdf`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

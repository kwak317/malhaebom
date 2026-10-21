import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ResumeDraftChat } from './ResumeDraftChat';

describe('이력서 채팅 초안의 자료 경계', () => {
  it('자료가 없으면 확인할 빈칸만 표시하고 예시 경력을 넣지 않는다', () => {
    const html = renderToStaticMarkup(<ResumeDraftChat layout="career" />);
    expect(html).toContain('[지원 직무 입력]');
    expect(html).toContain('[회사·직무·기간 입력 / 경력이 없으면 제외]');
    expect(html).not.toContain('가상테크');
    expect(html).not.toContain('Spring Boot');
  });
  it('확인한 채팅 경험은 텍스트로 표시하고 NCS는 참고용으로 분리한다', () => {
    const html = renderToStaticMarkup(<ResumeDraftChat layout="project" materials={{
      confirmedExperiences: ['<script>경험</script>'], ncsLabels: ['시스템 설계'],
      readmeAnalysis: { source_url: 'javascript:alert(1)', readme_sha: 'test', model: 'test', technology_stack: [], project_flow: [] },
    }} />);
    expect(html).toContain('&lt;script&gt;경험&lt;/script&gt;');
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('실제 보유 역량의 근거로 사용하지 않았어요');
  });
});

function renderLinks(text: string) {
  return text.split(/(https?:\/\/[^\s<>"']+)/g).map((part, index) => {
    if (!/^https?:\/\//.test(part)) return part;
    const url = part.replace(/[.,。)]+$/, "");
    return <span key={index}><a href={url} target="_blank" rel="noreferrer">{url}</a>{part.slice(url.length)}</span>;
  });
}

export function ChatMessageText({ text }: { text: string }) {
  return <p style={{ whiteSpace: "pre-wrap" }}>{text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    /^\*\*[^*]+\*\*$/.test(part)
      ? <strong key={index}>{renderLinks(part.slice(2, -2))}</strong>
      : <span key={index}>{renderLinks(part)}</span>,
  )}</p>;
}

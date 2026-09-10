import DOMPurify from 'dompurify';
import { marked } from 'marked';

marked.setOptions({
  gfm: true,
  breaks: true,
});

export const renderMarkdown = (text: string) => {
  const html = marked.parse(text || '', { async: false });
  return DOMPurify.sanitize(typeof html === 'string' ? html : String(html));
};

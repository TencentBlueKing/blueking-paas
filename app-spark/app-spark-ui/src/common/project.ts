export const generateProjectId = (): string => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let suffix = '';
  for (let i = 0; i < 10; i++) {
    suffix += chars[Math.floor(Math.random() * chars.length)];
  }
  return `p-${suffix}`;
};

export const projectNameFromPrompt = (prompt: string): string => {
  const name = prompt.trim();
  const characters = Array.from(name);
  return characters.length > 10 ? `${characters.slice(0, 10).join('')}...` : name;
};

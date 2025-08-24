export const computeProjectCompletion = (items) => {
  if (!items || !items.length) return 0;
  const sum = items.reduce((a, b) => a + (b.percentage || 0), 0);
  return Math.round(sum / items.length);
};
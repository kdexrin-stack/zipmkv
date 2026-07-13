export class DanmakuOptions {
  deleteNegative: boolean = true;
  stripAssTags: boolean = false;
  offsetSeconds: number = 0;
}

export function processDanmakuXml(source: string, options: DanmakuOptions): string {
  const pattern = /<d\s+([^>]*?p="([^"]+)"[^>]*)>([\s\S]*?)<\/d>/g;
  return source.replace(pattern, (_whole: string, attributes: string, packed: string, bodyValue: string): string => {
    const values = packed.split(',');
    const originalTime = Number(values[0]);
    const safeTime = Number.isFinite(originalTime) ? originalTime : 0;
    if (options.deleteNegative && safeTime < 0) {
      return '';
    }
    values[0] = Math.max(0, safeTime + options.offsetSeconds).toFixed(3);
    let body = bodyValue;
    if (options.stripAssTags) {
      body = body.replace(/\{\\[^}]+\}/g, '');
    }
    const updatedAttributes = attributes.replace(packed, values.join(','));
    return `<d ${updatedAttributes}>${body}</d>`;
  });
}

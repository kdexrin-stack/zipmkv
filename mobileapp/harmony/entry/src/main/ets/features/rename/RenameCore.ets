export class RenameRule {
  prefix: string = '';
  suffix: string = '';
  style: string = 'ep01';
  start: number = 1;
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.substring(dot) : '';
}

function sequenceLabel(value: number, style: string): string {
  if (style === 'ep1') {
    return `ep${value}`;
  }
  if (style === '01') {
    return value.toString().padStart(2, '0');
  }
  if (style === '1') {
    return value.toString();
  }
  return `ep${value.toString().padStart(2, '0')}`;
}

export function renamedFileName(originalName: string, index: number, rule: RenameRule): string {
  const value = Math.max(0, Math.floor(rule.start)) + index;
  return `${rule.prefix}${sequenceLabel(value, rule.style)}${rule.suffix}${extensionOf(originalName)}`;
}

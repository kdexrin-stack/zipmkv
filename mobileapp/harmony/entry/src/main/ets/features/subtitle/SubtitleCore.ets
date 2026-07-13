export class AssStyle {
  fontName: string = 'HarmonyOS Sans SC';
  fontSize: number = 48;
  primaryColor: string = '&H00FFFFFF';
  outlineColor: string = '&H00000000';
  outline: number = 2;
}

function normalized(text: string): string {
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function assTime(srtTime: string): string {
  const parts = srtTime.trim().replace(',', '.').split(':');
  if (parts.length !== 3) {
    return '0:00:00.00';
  }
  const secondsParts = parts[2].split('.');
  const hours = Number(parts[0]);
  const minutes = Number(parts[1]);
  const seconds = Number(secondsParts[0]);
  const milliseconds = Number((secondsParts.length > 1 ? secondsParts[1] : '0').padEnd(3, '0').substring(0, 3));
  const centiseconds = Math.floor(milliseconds / 10);
  return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${centiseconds.toString().padStart(2, '0')}`;
}

function styleLine(style: AssStyle, name: string = 'Default'): string {
  return `Style: ${name},${style.fontName},${style.fontSize},${style.primaryColor},&H000000FF,${style.outlineColor},&H64000000,0,0,0,0,100,100,0,0,1,${style.outline},0,2,20,20,24,1`;
}

function header(style: AssStyle): string {
  return `[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n${styleLine(style)}\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text`;
}

export function sampleStyle(sampleAss: string): AssStyle | undefined {
  const lines = normalized(sampleAss).split('\n');
  for (let index = 0; index < lines.length; index++) {
    if (!lines[index].startsWith('Style:')) {
      continue;
    }
    const values = lines[index].substring(6).trim().split(',');
    if (values.length < 17) {
      continue;
    }
    const style = new AssStyle();
    style.fontName = values[1].trim();
    style.fontSize = Number(values[2]) || 48;
    style.primaryColor = values[3].trim();
    style.outlineColor = values[5].trim();
    style.outline = Number(values[16]) || 2;
    return style;
  }
  return undefined;
}

export function srtToAss(source: string, style: AssStyle): string {
  const blocks = normalized(source).trim().split(/\n{2,}/);
  const events: Array<string> = [];
  blocks.forEach((block: string) => {
    const lines = block.split('\n');
    let timingIndex = 0;
    if (lines.length > 1 && /^\d+$/.test(lines[0].trim())) {
      timingIndex = 1;
    }
    if (timingIndex >= lines.length) {
      return;
    }
    const timing = lines[timingIndex].split('-->');
    if (timing.length !== 2) {
      return;
    }
    const text = lines.slice(timingIndex + 1).join('\\N')
      .replace(/<br\s*\/?>/gi, '\\N')
      .replace(/<[^>]+>/g, '');
    events.push(`Dialogue: 0,${assTime(timing[0])},${assTime(timing[1])},Default,,0,0,0,,${text}`);
  });
  return `${header(style)}\n${events.join('\n')}\n`;
}

export function applyStyleToAss(source: string, style: AssStyle): string {
  const lines = normalized(source).split('\n');
  let replaced = false;
  const updated: Array<string> = [];
  lines.forEach((line: string) => {
    if (line.startsWith('Style:')) {
      const values = line.substring(6).trim().split(',');
      const name = values.length > 0 && values[0].trim().length > 0 ? values[0].trim() : 'Default';
      updated.push(styleLine(style, name));
      replaced = true;
    } else {
      updated.push(line);
    }
  });
  if (replaced) {
    return `${updated.join('\n')}\n`;
  }
  const eventsIndex = updated.indexOf('[Events]');
  if (eventsIndex >= 0) {
    updated.splice(eventsIndex, 0, '[V4+ Styles]', 'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding', styleLine(style), '');
    return `${updated.join('\n')}\n`;
  }
  return `${header(style)}\n`;
}

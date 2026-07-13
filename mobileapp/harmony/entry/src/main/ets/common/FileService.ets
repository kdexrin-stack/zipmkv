import { common } from '@kit.AbilityKit';
import { buffer } from '@kit.ArkTS';
import { fileIo as fs, picker } from '@kit.CoreFileKit';

const MAX_TEXT_BYTES = 64 * 1024 * 1024;

export class PickedFile {
  uri: string;
  name: string;

  constructor(uri: string, name: string) {
    this.uri = uri;
    this.name = name;
  }
}

function fileNameFromUri(uri: string): string {
  const withoutQuery = uri.split('?')[0];
  const rawName = withoutQuery.substring(withoutQuery.lastIndexOf('/') + 1);
  try {
    return decodeURIComponent(rawName);
  } catch (_error) {
    return rawName;
  }
}

function suffixOf(fileName: string): string {
  const dot = fileName.lastIndexOf('.');
  return dot > 0 ? fileName.substring(dot) : '.txt';
}

export class FileService {
  static async pickFiles(context: common.Context, suffixChoices: Array<string>): Promise<Array<PickedFile>> {
    const options = new picker.DocumentSelectOptions();
    options.maxSelectNumber = 100;
    options.selectMode = picker.DocumentSelectMode.FILE;
    options.fileSuffixFilters = suffixChoices;
    const documentPicker = new picker.DocumentViewPicker(context);
    const uris = await documentPicker.select(options);
    const result: Array<PickedFile> = [];
    uris.forEach((uri: string) => {
      result.push(new PickedFile(uri, fileNameFromUri(uri)));
    });
    return result;
  }

  static readText(file: PickedFile): string {
    const handle = fs.openSync(file.uri, fs.OpenMode.READ_ONLY);
    try {
      const stat = fs.statSync(handle.fd);
      if (stat.size > MAX_TEXT_BYTES) {
        throw new Error(`文件超过文本处理上限 64 MB: ${file.name}`);
      }
      const data = new ArrayBuffer(stat.size);
      const length = fs.readSync(handle.fd, data, { offset: 0, length: stat.size });
      return buffer.from(data, 0, length).toString();
    } finally {
      fs.closeSync(handle);
    }
  }

  static async saveText(context: common.Context, fileName: string, content: string): Promise<string> {
    const options = new picker.DocumentSaveOptions();
    options.newFileNames = [fileName];
    options.fileSuffixChoices = [`文件|${suffixOf(fileName)}`];
    const documentPicker = new picker.DocumentViewPicker(context);
    const uris = await documentPicker.save(options);
    if (uris.length === 0) {
      throw new Error('未选择保存位置');
    }
    const handle = fs.openSync(uris[0], fs.OpenMode.READ_WRITE);
    try {
      fs.writeSync(handle.fd, content);
    } finally {
      fs.closeSync(handle);
    }
    return uris[0];
  }

  static async saveCopy(context: common.Context, source: PickedFile, outputName: string): Promise<string> {
    const options = new picker.DocumentSaveOptions();
    options.newFileNames = [outputName];
    options.fileSuffixChoices = [`文件|${suffixOf(outputName)}`];
    const documentPicker = new picker.DocumentViewPicker(context);
    const uris = await documentPicker.save(options);
    if (uris.length === 0) {
      throw new Error('未选择保存位置');
    }
    const sourceHandle = fs.openSync(source.uri, fs.OpenMode.READ_ONLY);
    const outputHandle = fs.openSync(uris[0], fs.OpenMode.READ_WRITE);
    try {
      fs.copyFileSync(sourceHandle.fd, outputHandle.fd);
    } finally {
      fs.closeSync(sourceHandle);
      fs.closeSync(outputHandle);
    }
    return uris[0];
  }
}

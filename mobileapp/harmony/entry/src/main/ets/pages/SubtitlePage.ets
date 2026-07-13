import { common } from '@kit.AbilityKit';
import { router } from '@kit.ArkUI';
import { FileService, PickedFile } from '../common/FileService';
import { applyStyleToAss, AssStyle, sampleStyle, srtToAss } from '../features/subtitle/SubtitleCore';

@Entry
@Component
struct SubtitlePage {
  @State files: Array<PickedFile> = [];
  @State sample: PickedFile | undefined = undefined;
  @State fontName: string = '';
  @State fontSize: string = '';
  @State primaryColor: string = '';
  @State outlineColor: string = '';
  @State outline: string = '';
  @State busy: boolean = false;
  @State status: string = '';

  private context(): common.Context {
    return this.getUIContext().getHostContext() as common.Context;
  }

  private async pickTargets(): Promise<void> {
    try {
      this.files = await FileService.pickFiles(this.context(), ['字幕|.srt,.ass,.ssa']);
      this.status = `已选择 ${this.files.length} 个字幕文件`;
    } catch (error) {
      this.status = `选择已取消或失败：${(error as Error).message}`;
    }
  }

  private async pickSample(): Promise<void> {
    try {
      const selected = await FileService.pickFiles(this.context(), ['ASS 样式示例|.ass,.ssa']);
      this.sample = selected.length > 0 ? selected[0] : undefined;
      this.status = this.sample ? `已选择示例：${this.sample.name}` : '未选择示例';
    } catch (error) {
      this.status = `示例选择已取消或失败：${(error as Error).message}`;
    }
  }

  private resolvedStyle(): AssStyle {
    let style = new AssStyle();
    if (this.sample) {
      const fromSample = sampleStyle(FileService.readText(this.sample));
      if (fromSample) {
        style = fromSample;
      }
    }
    if (this.fontName.trim().length > 0) {
      style.fontName = this.fontName.trim();
    }
    if (this.fontSize.trim().length > 0) {
      style.fontSize = Number(this.fontSize) || style.fontSize;
    }
    if (this.primaryColor.trim().length > 0) {
      style.primaryColor = this.primaryColor.trim();
    }
    if (this.outlineColor.trim().length > 0) {
      style.outlineColor = this.outlineColor.trim();
    }
    if (this.outline.trim().length > 0) {
      style.outline = Number(this.outline) || style.outline;
    }
    return style;
  }

  private async run(): Promise<void> {
    if (this.files.length === 0 || this.busy) {
      return;
    }
    this.busy = true;
    let saved = 0;
    try {
      const style = this.resolvedStyle();
      for (let index = 0; index < this.files.length; index++) {
        const file = this.files[index];
        this.status = `正在处理 ${index + 1}/${this.files.length}：${file.name}`;
        const source = FileService.readText(file);
        const output = file.name.toLowerCase().endsWith('.srt') ? srtToAss(source, style) : applyStyleToAss(source, style);
        const baseName = file.name.replace(/\.(srt|ass|ssa)$/i, '');
        await FileService.saveText(this.context(), `${baseName}_modified.ass`, output);
        saved++;
      }
      this.status = `完成：已生成 ${saved} 个 ASS，手动非空参数优先于示例`;
    } catch (error) {
      this.status = `已保存 ${saved} 个；操作中止：${(error as Error).message}`;
    } finally {
      this.busy = false;
    }
  }

  build() {
    Column() {
      Row({ space: 12 }) {
        Button('‹').type(ButtonType.Normal).onClick(() => router.back())
        Text('字幕样式处理').fontSize(21).fontWeight(FontWeight.Bold)
      }
      .width('100%')
      .padding(16)
      .backgroundColor('#FFFFFF')

      Scroll() {
        Column({ space: 10 }) {
          Button(this.files.length === 0 ? '选择 SRT / ASS 字幕' : `重新选择目标（${this.files.length}）`)
            .width('100%')
            .enabled(!this.busy)
            .onClick(() => this.pickTargets())

          Button(this.sample ? `示例：${this.sample.name}` : '选择 ASS 样式示例（可选）')
            .width('100%')
            .enabled(!this.busy)
            .onClick(() => this.pickSample())

          Text('手动参数（留空时使用示例；无示例则使用默认值）')
            .fontSize(13)
            .fontColor('#475467')
            .width('100%')
            .margin({ top: 6 })

          TextInput({ text: this.fontName, placeholder: '字体，例如 HarmonyOS Sans SC' })
            .onChange((value: string) => this.fontName = value)
          Row({ space: 10 }) {
            TextInput({ text: this.fontSize, placeholder: '字号，例如 48' })
              .type(InputType.Number)
              .layoutWeight(1)
              .onChange((value: string) => this.fontSize = value)
            TextInput({ text: this.outline, placeholder: '描边，例如 2' })
              .type(InputType.Number)
              .layoutWeight(1)
              .onChange((value: string) => this.outline = value)
          }
          TextInput({ text: this.primaryColor, placeholder: '主颜色，例如 &H00FFFFFF' })
            .onChange((value: string) => this.primaryColor = value)
          TextInput({ text: this.outlineColor, placeholder: '描边颜色，例如 &H00000000' })
            .onChange((value: string) => this.outlineColor = value)

          Button(this.busy ? '处理中…' : '生成 ASS 字幕')
            .width('100%')
            .enabled(!this.busy && this.files.length > 0)
            .onClick(() => this.run())

          Text(this.status)
            .fontSize(13)
            .fontColor('#344054')
            .width('100%')
            .minHeight(54)
            .padding(10)
        }
        .width('100%')
        .padding(16)
      }
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F6F7F9')
  }
}

import { common } from '@kit.AbilityKit';
import { router } from '@kit.ArkUI';
import { FileService, PickedFile } from '../common/FileService';
import { DanmakuOptions, processDanmakuXml } from '../features/danmaku/DanmakuCore';

@Entry
@Component
struct DanmakuPage {
  @State files: Array<PickedFile> = [];
  @State deleteNegative: boolean = true;
  @State stripAssTags: boolean = false;
  @State offsetValue: string = '0';
  @State busy: boolean = false;
  @State status: string = '';

  private context(): common.Context {
    return this.getUIContext().getHostContext() as common.Context;
  }

  private async pick(): Promise<void> {
    try {
      this.files = await FileService.pickFiles(this.context(), ['XML 弹幕|.xml']);
      this.status = `已选择 ${this.files.length} 个 XML 文件`;
    } catch (error) {
      this.status = `选择已取消或失败：${(error as Error).message}`;
    }
  }

  private async run(): Promise<void> {
    if (this.files.length === 0 || this.busy) {
      return;
    }
    this.busy = true;
    let saved = 0;
    const options = new DanmakuOptions();
    options.deleteNegative = this.deleteNegative;
    options.stripAssTags = this.stripAssTags;
    options.offsetSeconds = Number(this.offsetValue) || 0;
    try {
      for (let index = 0; index < this.files.length; index++) {
        const file = this.files[index];
        this.status = `正在处理 ${index + 1}/${this.files.length}：${file.name}`;
        const source = FileService.readText(file);
        const output = processDanmakuXml(source, options);
        const outputName = file.name.replace(/\.xml$/i, '_modified.xml');
        await FileService.saveText(this.context(), outputName, output);
        saved++;
      }
      this.status = `完成：已生成 ${saved} 个 XML，源文件未修改`;
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
        Text('XML 弹幕批量处理').fontSize(21).fontWeight(FontWeight.Bold)
      }
      .width('100%')
      .padding(16)
      .backgroundColor('#FFFFFF')

      Scroll() {
        Column({ space: 10 }) {
          Button(this.files.length === 0 ? '选择一个或多个 XML' : `重新选择（${this.files.length}）`)
            .width('100%')
            .enabled(!this.busy)
            .onClick(() => this.pick())

          Row() {
            Text('删除负时间弹幕').layoutWeight(1).fontSize(15)
            Toggle({ type: ToggleType.Switch, isOn: this.deleteNegative })
              .onChange((value: boolean) => this.deleteNegative = value)
          }
          .width('100%')
          .padding(12)
          .backgroundColor('#FFFFFF')

          Row() {
            Text('清理 ASS 样式标签').layoutWeight(1).fontSize(15)
            Toggle({ type: ToggleType.Switch, isOn: this.stripAssTags })
              .onChange((value: boolean) => this.stripAssTags = value)
          }
          .width('100%')
          .padding(12)
          .backgroundColor('#FFFFFF')

          TextInput({ text: this.offsetValue, placeholder: '整体平移秒数，可为负数' })
            .type(InputType.Number)
            .onChange((value: string) => this.offsetValue = value)

          Button(this.busy ? '处理中…' : '生成处理后的 XML')
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

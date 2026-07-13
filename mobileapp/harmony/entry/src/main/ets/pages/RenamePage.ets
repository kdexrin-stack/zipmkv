import { common } from '@kit.AbilityKit';
import { router } from '@kit.ArkUI';
import { FileService, PickedFile } from '../common/FileService';
import { RenameRule, renamedFileName } from '../features/rename/RenameCore';

@Entry
@Component
struct RenamePage {
  @State files: Array<PickedFile> = [];
  @State prefix: string = '';
  @State suffix: string = '';
  @State startValue: string = '1';
  @State styleIndex: number = 1;
  @State busy: boolean = false;
  @State status: string = '';
  private styles: Array<string> = ['ep1', 'ep01', '01', '1'];

  private context(): common.Context {
    return this.getUIContext().getHostContext() as common.Context;
  }

  private rule(): RenameRule {
    const rule = new RenameRule();
    rule.prefix = this.prefix;
    rule.suffix = this.suffix;
    rule.style = this.styles[this.styleIndex];
    rule.start = Number(this.startValue) || 1;
    return rule;
  }

  private async pick(): Promise<void> {
    try {
      this.files = await FileService.pickFiles(this.context(), ['所有文件(*.*)|.*']);
      this.status = `已选择 ${this.files.length} 个文件`;
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
    try {
      const rule = this.rule();
      for (let index = 0; index < this.files.length; index++) {
        this.status = `正在保存 ${index + 1}/${this.files.length}`;
        await FileService.saveCopy(this.context(), this.files[index], renamedFileName(this.files[index].name, index, rule));
        saved++;
      }
      this.status = `完成：已生成 ${saved} 个无损副本，源文件未修改`;
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
        Text('批量文件重命名').fontSize(21).fontWeight(FontWeight.Bold)
      }
      .width('100%')
      .padding(16)
      .backgroundColor('#FFFFFF')

      Scroll() {
        Column({ space: 12 }) {
          Button(this.files.length === 0 ? '选择一个或多个文件' : `重新选择（${this.files.length}）`)
            .width('100%')
            .enabled(!this.busy)
            .onClick(() => this.pick())

          Row({ space: 10 }) {
            TextInput({ text: this.prefix, placeholder: '固定前缀，例如 视频' })
              .layoutWeight(1)
              .onChange((value: string) => this.prefix = value)
            TextInput({ text: this.suffix, placeholder: '固定后缀，例如 完结' })
              .layoutWeight(1)
              .onChange((value: string) => this.suffix = value)
          }

          Row({ space: 10 }) {
            Select(this.styles.map((value: string) => ({ value: value })))
              .selected(this.styleIndex)
              .layoutWeight(1)
              .onSelect((index: number) => this.styleIndex = index)
            TextInput({ text: this.startValue, placeholder: '起始序号' })
              .type(InputType.Number)
              .layoutWeight(1)
              .onChange((value: string) => this.startValue = value)
          }

          Column({ space: 6 }) {
            Text('效果预览').fontSize(14).fontWeight(FontWeight.Medium).width('100%')
            ForEach(this.files.slice(0, 5), (file: PickedFile, index: number) => {
              Text(`${file.name}  →  ${renamedFileName(file.name, index, this.rule())}`)
                .fontSize(12)
                .fontColor('#475467')
                .width('100%')
                .maxLines(2)
            }, (file: PickedFile) => file.uri)
          }
          .width('100%')
          .padding(12)
          .backgroundColor('#FFFFFF')
          .border({ width: 1, color: '#E4E7EC', radius: 8 })

          Button(this.busy ? '处理中…' : '生成重命名副本')
            .width('100%')
            .enabled(!this.busy && this.files.length > 0)
            .onClick(() => this.run())

          Text(this.status)
            .fontSize(13)
            .fontColor('#344054')
            .width('100%')
            .minHeight(42)
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

import { router } from '@kit.ArkUI';
import { TOOL_MODULES, ToolModule } from '../models/ToolModule';

@Entry
@Component
struct Index {
  build() {
    Column() {
      Column() {
        Text('zipmkv')
          .fontSize(30)
          .fontWeight(FontWeight.Bold)
          .fontColor('#182230')
        Text('本地文件与字幕工具')
          .fontSize(15)
          .fontColor('#667085')
          .margin({ top: 4 })
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)
      .padding({ left: 20, right: 20, top: 22, bottom: 16 })

      Scroll() {
        Column({ space: 10 }) {
          ForEach(TOOL_MODULES, (module: ToolModule) => {
            Row({ space: 14 }) {
              Text(module.symbol)
                .fontSize(20)
                .fontWeight(FontWeight.Medium)
                .fontColor('#FFFFFF')
                .width(44)
                .height(44)
                .textAlign(TextAlign.Center)
                .backgroundColor('#1769E0')
                .borderRadius(8)
              Column({ space: 4 }) {
                Text(module.title)
                  .fontSize(17)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#182230')
                  .width('100%')
                Text(module.description)
                  .fontSize(13)
                  .fontColor('#667085')
                  .width('100%')
                  .maxLines(2)
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              Text('›')
                .fontSize(28)
                .fontColor('#98A2B3')
            }
            .width('100%')
            .padding(14)
            .border({ width: 1, color: '#E4E7EC', radius: 8 })
            .backgroundColor('#FFFFFF')
            .onClick(() => {
              router.pushUrl({ url: module.route });
            })
          }, (module: ToolModule) => module.id)

          Text('所有处理均由用户选择输入和保存位置，不覆盖源文件。')
            .fontSize(12)
            .fontColor('#667085')
            .width('100%')
            .textAlign(TextAlign.Center)
            .margin({ top: 12, bottom: 28 })
        }
        .width('100%')
        .padding({ left: 16, right: 16 })
      }
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F6F7F9')
  }
}

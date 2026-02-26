
import "utils.js" as Utils
MbItemCol {
    id: root

    description: qsTr("BattInfo")

    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0

    height: nBatt*mbStyle.itemHeight

    function ibrRepeater() {
        let list = []
        var comp = Qt.createComponent("IbrBattInfoDetail.qml");
        for (var index = 0; index < nBatt; index++)
            list.push(
                comp.createObject(root, {
                    description: battInfo.value[index*3],
                    battName: battInfo.value[index*3+1],
                    battId: battInfo.value[index*3+2] }
                )
            )
        return list;
    }

    values: ibrRepeater()
}


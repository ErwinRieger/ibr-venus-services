
// import QtQuick 1.1
import "utils.js" as Utils
MbItemCol {
    id: root

    description: qsTr("BattInfo")
    property IbrSmallStyle mbStyle: IbrSmallStyle {}

    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0

    height: nBatt*mbStyle.itemHeight

    values: [
	    Repeater {
            model: nBatt
            IbrBattInfoRow {
                battDevice: battInfo.value[index*3] // batt device
                battName: battInfo.value[index*3+1]
                battId: battInfo.value[index*3+2]
            }
        }
    ]
}


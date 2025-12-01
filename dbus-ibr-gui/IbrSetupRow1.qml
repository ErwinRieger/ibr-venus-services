
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
                        MbItemRow {
                            VBusItem { id: battDevice; value: battInfo.value[index*3] }
                            VBusItem { id: battName; value: battInfo.value[index*3+1] }
                            VBusItem { id: btId; value: battInfo.value[index*3+2] }
                            description: battDevice.value
                            mbStyle: IbrSmallStyle {}
                            values: [
                                MbTextBlock {
                                    item: battName
                                    mbStyle: IbrSmallStyle {}
                                },
                                MbTextBlock {
                                    item: btId
                                    mbStyle: IbrSmallStyle {}
                                }
                            ]
                        }
                    }
    ]
}



import "utils.js" as Utils

MbItemCol {
   
    id: root
 
    property variant bmsService
    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0

    description: qsTr("Batt")

    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    height: (nBatt+1)*mbStyle.itemHeight

    values: [
        IbrBattInfoBms {
            bmsService: root.bmsService 
        }
    ]

    function ibrRepeater() {
        var comp = Qt.createComponent("IbrBattInfoRow.qml");
        if (comp.status == Component.Error) {
                 console.log("Error loading component:", comp.errorString());
        }
        for (var index = 0; index < nBatt; index++) {
            var obj = comp.createObject(null, {
                     bindPrefix: bmsService.name,
                     description: battInfo.value[index*3+1],
                     battDevice: battInfo.value[index*3] })
             values.push(obj)
        }
     }
    
    Component.onCompleted: { ibrRepeater() }
}


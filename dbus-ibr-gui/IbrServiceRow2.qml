
import "utils.js" as Utils

MbItemCol {
   
    id: root
 
    property variant bmsService
    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0

    description: qsTr("Batt")

    // mbStyle: IbrSmallStyle { }
    property IbrSmallStyle mbStyle: IbrSmallStyle {}
    height: (nBatt+1)*mbStyle.itemHeight

    function ibrRepeater() {

        var comp = Qt.createComponent("IbrBattInfoBms.qml");
        if (comp.status == Component.Error) {
                 console.log("Error loading component:", comp.errorString());
        }
        var obj = comp.createObject(null, { bmsService: root.bmsService } )
        if (obj == null) {
            console.log("Error creating PageIbrServices object");
        }
        
        let list = [ obj ]
        comp = Qt.createComponent("IbrBattInfoRow.qml");
        if (comp.status == Component.Error) {
                 console.log("Error loading component:", comp.errorString());
        }
        for (var index = 0; index < nBatt; index++) {
            obj = comp.createObject(null, {
                     bindPrefix: bmsService.name,
                     description: battInfo.value[index*3+1],
                     battDevice: battInfo.value[index*3] })
             list.push(obj)
        }
        return list;
     }
    
	 values: ibrRepeater()
}


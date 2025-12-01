import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils

// contentItem

MbPage {
	id: root

    property string bindPrefix   // our service name
    property variant service     // our service

	title: "IBR Services" // service.description
	summary: "summary" // (!isParallelBms && state.item.value === 18) ? "Pending " + dcVoltage.text + " " + soc.item.format(0) : [soc.item.format(0), dcVoltage.text, dcCurrent.text]

    property VBusItem bmsItems: VBusItem { bind: Utils.path("com.victronenergy.system", "/AvailableBmsServices") } 
    property VBusItem battInfo: VBusItem { bind: Utils.path("com.victronenergy.ibrsystem", "/Info/BattInfo") } 
    property VBusItem balanersRunning: VBusItem { bind: Utils.path(bindPrefix, "/Ess/Balancing") } 

    property variant sys: theSystem

	property MbStyle smallStyle: MbStyle { fontPixelSize: 14; itemHeight: 23; marginItemHorizontal: 2; marginItemVertical: 2; }

    property int nBatt: battInfo.valid ? (battInfo.value.length/3) : 0


    model: VisibleItemModel {

        // IbrServiceRow1 { bmsService: root.servcie; }
        IbrServiceRow1 { }
        // IbrServiceRow2 { bmsService: root.servcie; }
        // IbrServiceRow3 { bmsService: root.servcie; }
        // IbrServiceRow4 { bmsService: root.servcie; }
        IbrServiceDetails { bmsService: root.servcie; }

  } // visiblemodel

} // Page

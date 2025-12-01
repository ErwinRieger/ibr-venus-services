
MbItemCol {

    description: qsTr("PV")

    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    height: 2*mbStyle.itemHeight

    function mpptModeAsString(mode) {
	    switch (mode) {
	        case 0:
		        return "off"
	        case 1:
		        return "idle"
	        case 2:
		        return "run"
	    }
        return "--"
    }

    VBusItem { id:mpptmode; bind: "com.victronenergy.ibrsystem/MppOperationMode" }

    values: [
            MbItemRow {
		        description: qsTr("Erzeug:")
                mbStyle: IbrSmallStyle { }
			    values: [
                    MbTextBlock { 
                        item: VBusItem { value: mpptModeAsString(mpptmode.value) }
                        mbStyle: IbrSmallStyle { }
                    },
                    MbTextBlock { 
                      item: theSystem.pvCharger.power
                      mbStyle: IbrSmallStyle { }
                    },
                    MbTextBlock { 
                      item.bind: "com.victronenergy.ibrsystem/TotalPVYield";
                      mbStyle: IbrSmallStyle { }
                      item.decimals:3;
                      item.unit: "kWh"
                    }
                ]
            },
            MbItemRow {
		        description: qsTr("Ertrag:")
                mbStyle: IbrSmallStyle { }
			    values: MbTextBlock { 
                item.bind: "com.victronenergy.ibrsystem/TotalPVEarnings";
                mbStyle: IbrSmallStyle { }
                item.decimals:3;
                item.unit: "Eur"
            }
        }
    ]
}


MbItemCol {

    description: qsTr("PV")
    property IbrSmallStyle mbStyle: IbrSmallStyle {}
    property variant sys: theSystem

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

     height: 2*mbStyle.itemHeight
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
                    item: sys.pvCharger.power
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


MbItemCol {
    description: qsTr("PV")

    // property IbrSmallStyle mbStyle: IbrSmallStyle {}
    mbStyle.fontPixelSize: 14
    mbStyle.itemHeight: 23
    mbStyle.marginItemHorizontal: 2
    mbStyle.marginItemVertical: 2

    property variant sys: theSystem

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


MbItemCol {
		 description: qsTr("Batt")
         height: (nBatt+1)*root.smallStyle.itemHeight
         VBusItem { id:cv; bind: service.path("/Info/MaxChargeVoltage") }
		 values: [
                  // Cv, Volt, Current, Min, Max, Soc
                  MbItemRow {
		            description: qsTr("BMS:")
                    mbStyle: IbrSmallStyle { }
			        values: [
                      MbTextBlock { 
                          item: VBusItem { value: "cv "+cv.format(2)+"V" }
                          mbStyle: IbrSmallStyle { }
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Voltage");
                    mbStyle: IbrSmallStyle { }
                        item.decimals:2;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Dc/0/Current");
                    mbStyle: IbrSmallStyle { }
                        item.decimals:1;
                        item.unit: "A"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MinCellVoltage");
                    mbStyle: IbrSmallStyle { }
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/System/MaxCellVoltage");
                    mbStyle: IbrSmallStyle { }
                        item.decimals:3;
                        item.unit: "V"
                      },
                      MbTextBlock { 
                        item.bind: service.path("/Soc");
                        mbStyle: IbrSmallStyle { }
                        item.decimals:1;
                        item.unit: "%"
                      }
                    ]
                  },
		          Repeater {
          			model: nBatt

                        // Current, Min, Max, Soc
          				// opacity: getScaledStrength(strength.value) >= (index + 1) ? 1 : 0.2
                        MbItemRow {
                            property string battDevice: battInfo.value[index*3]
                            property string battPath: "com.victronenergy.battery."+battDevice
	                        property string balancer:  ((balanersRunning.value !== undefined && balanersRunning.value.includes(battDevice)) ? "B on " : "B off")
	                        property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }
		                    description: qsTr(battInfo.value[index*3+1])
                            mbStyle: IbrSmallStyle { }
			                values: [
                                MbTextBlock { 
                                    item: VBusItem { value: balancer }
                                    mbStyle: IbrSmallStyle { }
                                },
                                MbTextBlock { 
                                    item: VBusItem { value: vdiff.value*1000; decimals: 0; unit: "mV" }
                                    mbStyle: IbrSmallStyle { }
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Dc/0/Current";
                                    mbStyle: IbrSmallStyle { }
                                    item.decimals:1;
                                    item.unit: "A"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MinCellVoltage";
                                    mbStyle: IbrSmallStyle { }
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/System/MaxCellVoltage";
                                    mbStyle: IbrSmallStyle { }
                                    item.decimals:3;
                                    item.unit: "v"
                                },
                                MbTextBlock { 
                                    item.bind: battPath+"/Soc";
                                    mbStyle: IbrSmallStyle { }
                                    item.decimals:1;
                                    item.unit: "%"
                                }
                        ]
                    }
      			}
		 ]
}


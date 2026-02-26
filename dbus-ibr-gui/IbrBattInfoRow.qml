
import "utils.js" as Utils

// Current, Min, Max, Soc
// opacity: getScaledStrength(strength.value) >= (index + 1) ? 1 : 0.2
MbItemRow {
    property string battDevice
    property string bindPrefix   // our service name

    property string battPath: "com.victronenergy.battery."+battDevice

    property VBusItem balanersRunning: VBusItem { bind: Utils.path(bindPrefix, "/Ess/Balancing") } 
    property string balancer:  ((balanersRunning.value !== undefined && balanersRunning.value.includes(battDevice)) ? "B on " : "B off")

    property VBusItem vdiff: VBusItem { bind: battPath+"/Voltages/Diff" }

    mbStyle: IbrSmallStyle { }

    values: [
        MbTextBlock { 
            item.text: balancer
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



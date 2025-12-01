import com.victron.velib 1.0

MbPage {                                                                                                                                                      
    id: root                                                                                                                                          
    property variant bmsService
                                                                                                                                                      
    model: VisibleItemModel {                                                                                                                         
        IbrSetupRow1 { }
        IbrSetupRow2 { bmsService: root.bmsService; }
        IbrSetupEdit { bindPrefix: "com.victronenergy.settings"; } // xxx move to subcomponent
    }                                                                                                                                                 
} 

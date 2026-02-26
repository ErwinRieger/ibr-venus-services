
import "utils.js" as Utils                                                                                                                            

MbEditBox {
        property string bindPrefix
        description: qsTr("Energy Price")                                                                                                             
        matchString: "0123456789.,"                                                                                                                   
        maximumLength: 3                                                                                                                              
        item {
            bind: Utils.path(bindPrefix, "/Settings/IbrSystem/GridEnergyPrice")                                                                       
        }
}                                                                                                                                                     
    


MbSubMenu {
    id: root
    property variant bmsService
    description: qsTr("Details/Settings")
    subpage: PageIbrServicesSetup {
        title: root.description
        bmsService: root.bmsService
    }
}

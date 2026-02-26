
MbSubMenu {
    id: root
    property variant bmsService
    description: qsTr("Details")
    subpage: PageIbrServicesSetup {
        title: root.description
        bmsService: root.bmsService
    }
}

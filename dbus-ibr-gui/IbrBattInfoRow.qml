
MbItemRow {

    property string battDevice
    property string battName
    property string battId

    description: battDevice // battInfo.value[index*3] // batt device
    mbStyle: IbrSmallStyle {}

    values: [
        MbTextBlock {
            item.text: battName
            mbStyle: IbrSmallStyle {}
        },
        MbTextBlock {
            item.text: battId
            mbStyle: IbrSmallStyle {}
        }
    ]
}


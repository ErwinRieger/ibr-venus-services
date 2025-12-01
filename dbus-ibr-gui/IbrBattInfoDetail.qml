
MbItemRow {

    property string battName
    property string battId

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


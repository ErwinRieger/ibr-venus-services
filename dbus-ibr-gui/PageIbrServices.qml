import com.victron.velib 1.0

MbPage {
	id: root

    property string bindPrefix   // our service name
    property variant service     // our service

	title: "IBR Services"
	summary: "summary" // (!isParallelBms && state.item.value === 18) ? "Pending " + dcVoltage.text + " " + soc.item.format(0) : [soc.item.format(0), dcVoltage.text, dcCurrent.text]

    model: VisibleItemModel {

        IbrServiceRow1 { }
        IbrServiceRow2 { bmsService: root.service; }
        IbrServiceRow3 { }
        IbrServiceDetails { bmsService: root.service; }

  } // visiblemodel

} // Page


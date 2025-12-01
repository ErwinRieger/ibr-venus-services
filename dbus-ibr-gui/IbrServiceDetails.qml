// import QtQuick 1.1
// import com.victron.velib 1.0
// import "utils.js" as Utils

MbSubMenu {
			id: root
            property variant bmsService
			description: qsTr("Details")
			subpage: Component {
				PageIbrServicesSetup {
					title: root.description
					bmsService: root.bmsService
				}
			}
}

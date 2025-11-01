import QtQuick 2
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
	id: root
	property bool show: true // allowedRoles.valid
	property string bindPrefix
	property int productId


	property int em24ProductId: 0xb017
	property int smappeeProductId: 0xb018

	function getRoleName(r)
	{
		switch (r) {
		case "grid":
			return qsTr("Grid meter");
		case "pvinverter":
			return qsTr("PV inverter");
		case "genset":
			return qsTr("Generator");
		case "acload":
			return qsTr("AC load");
		case "evcharger":
			return qsTr("EV Charger");
		case "heatpump":
			return qsTr("Heat pump");
		default:
			return '--';
		}
	}

	Component {
		id: mbOptionFactory
		MbOption {}
	}

	function getRoleList(roles)
	{
		if (!roles)
			return [];

		var options = [];
		for (var i = 0; i < roles.length; i++) {
			var params = {
				"description": getRoleName(roles[i]),
				"value": roles[i],
				"readonly": roles[i] === "heatpump",
			}
			options.push(mbOptionFactory.createObject(root, params));
		}

		return options;
	}

	/*
	 * This is a bit weird, when changing the role in a cgwacs service, it will
	 * directly disconnect, without a reply or signal that the value changed. So
	 * the gui blindly trust the remote for now to change its servicename and
	 * wait for it, which can take up to some seconds. It is not reacting in
	 * the meantime, but also not stuck. Eventually it ends up finding the new
	 * service, but it would not hurt to find a better way to do this.
	 */
	function updateServiceName(role)
	{
		var s = bindPrefix.split('.');

		if (s[2] === role)
			return;

		s[2] = role;
		bindPrefix = s.join('.');
	}

	// function em24Locked() { return em24SwitchPos.item.valid && em24SwitchPos.item.value == 3; }

	function em24SwitchText(pos)
	{
		switch (pos) {
		case 0: return qsTr("Unlocked (kVARh)");
		case 1: return qsTr("Unlocked (2)");
		case 2: return qsTr("Unlocked (1)");
		case 3: return qsTr("Locked");
		}
		return qsTr("Unknown");
	}

	// VBusItem {
		// id: allowedRoles
		// bind: Utils.path(root.bindPrefix, "/AllowedRoles")
		// onValueChanged: role.possibleValues = getRoleList(value)
	// }

	model: VisibleItemModel {

		MbEditBox {
			description: qsTr("Energy Price")
            matchString: "0123456789.,"
            maximumLength: 3 
			item {
				bind: Utils.path(root.bindPrefix, "/Settings/IbrSystem/GridEnergyPrice")
				// text: item.valid ? em24SwitchText(item.value) : "--"
			}
		}

	}
}


/**
 * Similar to MbItemRow but uses a Column to show several rows on the right side.
 */

MbItem {
    id: root

	property alias description: _description.text
	default property alias values: _values.data
	property alias fontFamily: _description.font.family

	// The description of the values shown
	MbTextDescription {
		id: _description
		anchors {
			left: root.left; leftMargin: mbStyle.marginDefault
			verticalCenter: parent.verticalCenter
		}
	}

	// The actual values
    MbColumn {
	  id: _values
      width: root.width - (_description.x + _description.width) - 20
      // height: parent.height;
      anchors {
			right: parent.right; rightMargin: mbStyle.marginDefault
			// verticalCenter: parent.verticalCenter
      }
      spacing: 0
    }
}

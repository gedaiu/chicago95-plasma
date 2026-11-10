import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_buttonText: buttonText.text
    property string cfg_logo

    readonly property bool customLogo: cfg_logo !== "flag" && cfg_logo !== "penguin"

    Kirigami.FormLayout {
        QQC2.ComboBox {
            id: textChoice
            Kirigami.FormData.label: "Text:"
            model: ["Start", "Linux", "Custom"]
            currentIndex: buttonText.text === "Start" ? 0 : buttonText.text === "Linux" ? 1 : 2
            onActivated: index => { if (index < 2) buttonText.text = model[index] }
        }
        QQC2.TextField {
            id: buttonText
            visible: textChoice.currentIndex === 2
            Kirigami.FormData.label: "Custom text:"
        }
        QQC2.ComboBox {
            id: logoChoice
            Kirigami.FormData.label: "Logo:"
            model: ["Classic flag", "Penguin", "Custom image"]
            currentIndex: cfg_logo === "flag" ? 0 : cfg_logo === "penguin" ? 1 : 2
            onActivated: index => { cfg_logo = index === 0 ? "flag" : index === 1 ? "penguin" : "" }
        }
        QQC2.TextField {
            visible: logoChoice.currentIndex === 2
            Kirigami.FormData.label: "Image file:"
            placeholderText: "/home/you/Pictures/logo.png"
            text: customLogo ? cfg_logo : ""
            onTextEdited: cfg_logo = text
        }
    }
}

.pragma library

function nativeFamily(look, scale, families) {
    let family;
    if (look === "1995" || look === "1998") {
        if (scale !== 1 && scale !== 1.25)
            return "";
        family = "Chicago95 Windows " + look.slice(-2) + (scale === 1.25 ? " 120 DPI" : "");
    } else if (look === "2000") {
        family = "Chicago95 Windows 2000 Tahoma";
    } else if (look === "2001") {
        family = "Tahoma";
    }
    return families.includes(family) ? family : "";
}

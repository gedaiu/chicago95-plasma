.pragma library

function timeFormat(hourFormat, localeShortFormat) {
  if (hourFormat === "24") return "HH:mm";
  if (hourFormat === "12") return "h:mm AP";

  return localeShortFormat;
}

// Windows 7's notification area spells the year in full (10/26/2009) whatever the short format.
function fullYearDateFormat(localeShortFormat) {
  return localeShortFormat.includes("yyyy") ? localeShortFormat : localeShortFormat.replace("yy", "yyyy");
}

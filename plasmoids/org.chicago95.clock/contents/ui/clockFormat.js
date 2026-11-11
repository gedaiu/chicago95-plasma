.pragma library

function timeFormat(hourFormat, localeShortFormat) {
  if (hourFormat === "24") return "HH:mm";
  if (hourFormat === "12") return "h:mm AP";

  return localeShortFormat;
}

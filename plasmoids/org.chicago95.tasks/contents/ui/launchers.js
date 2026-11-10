.pragma library

const CELL_WIDTH = 23
const REMOVE_DISTANCE = 12

function insertionIndexAt(x, quickLaunchX, count) {
    const gap = Math.round((x - quickLaunchX) / CELL_WIDTH)
    return Math.max(0, Math.min(count, gap))
}

function dragResult(fromIndex, x, y, width, height, quickLaunchX, count) {
    const offTaskbar = x < -REMOVE_DISTANCE || x > width + REMOVE_DISTANCE || y < -REMOVE_DISTANCE || y > height + REMOVE_DISTANCE
    if (offTaskbar)
        return { action: "remove", to: -1 }
    const gap = insertionIndexAt(x, quickLaunchX, count)
    const to = gap > fromIndex ? gap - 1 : gap
    return to === fromIndex ? { action: "none", to: -1 } : { action: "move", to: to }
}

// macOS shaping probe: swift font-build/shape.swift path/to/font.ttf text tag=value ...
import Foundation
import CoreText
import CoreGraphics

let args = Array(CommandLine.arguments.dropFirst())
let url = URL(fileURLWithPath: args[0])
let provider = CGDataProvider(url: url as CFURL)!
let graphicsFont = CGFont(provider)!
let settings: [[String: Any]] = args.dropFirst(2).map { option in
    let values = option.split(separator: "=")
    return [kCTFontOpenTypeFeatureTag as String: String(values[0]),
            kCTFontOpenTypeFeatureValue as String: Int(values[1])!]
}
let descriptor = CTFontDescriptorCreateWithAttributes([kCTFontFeatureSettingsAttribute as String: settings] as CFDictionary)
let font = CTFontCreateWithGraphicsFont(graphicsFont, 1600, nil, descriptor)
var attributes: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font]
if args.dropFirst(2).contains("kern=0") {
    attributes[NSAttributedString.Key(kCTKernAttributeName as String)] = 0
}
let string = NSAttributedString(string: args[1], attributes: attributes)
let line = CTLineCreateWithAttributedString(string)
var results: [[String: Any]] = []
for run in CTLineGetGlyphRuns(line) as! [CTRun] {
    let count = CTRunGetGlyphCount(run)
    var glyphs = [CGGlyph](repeating: 0, count: count)
    var advances = [CGSize](repeating: .zero, count: count)
    CTRunGetGlyphs(run, CFRangeMake(0, 0), &glyphs)
    CTRunGetAdvances(run, CFRangeMake(0, 0), &advances)
    for i in 0..<count {
        results.append(["name": graphicsFont.name(for: glyphs[i])! as String,
                        "advance": advances[i].width])
    }
}
let result = try! JSONSerialization.data(withJSONObject: results, options: [.sortedKeys])
print(String(data: result, encoding: .utf8)!)

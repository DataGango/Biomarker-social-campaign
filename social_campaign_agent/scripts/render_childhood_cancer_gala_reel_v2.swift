import AVFoundation
import CoreGraphics
import CoreText
import CoreVideo
import Foundation

struct Scene {
    let eyebrow: String
    let headline: String
    let body: String
    let footer: String
    let background: CGColor
}

let outputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let width = 720
let height = 1280
let fps: Int32 = 24
let secondsPerScene = 5
let scenes = [
    Scene(
        eyebrow: "FAIRFAX + DMV COMMUNITY",
        headline: "Make an evening count",
        body: "Come together for children facing cancer.",
        footer: "Independent community invitation",
        background: CGColor(red: 0.09, green: 0.20, blue: 0.17, alpha: 1)
    ),
    Scene(
        eyebrow: "A FUNDRAISING EVENING",
        headline: "Children's Cancer Foundation\n42nd Annual Gala",
        body: "Saturday, November 7, 2026\n7:00-11:00 PM EST",
        footer: "A regional invitation for Fairfax and the DMV",
        background: CGColor(red: 0.16, green: 0.24, blue: 0.22, alpha: 1)
    ),
    Scene(
        eyebrow: "THE ACTUAL VENUE",
        headline: "Greenbelt, Maryland\nNot Fairfax",
        body: "Martin's Crosswinds\n7400 Greenway Center Dr\nGreenbelt, MD 20770",
        footer: "Check the official event page before traveling",
        background: CGColor(red: 0.12, green: 0.22, blue: 0.20, alpha: 1)
    ),
    Scene(
        eyebrow: "TAKE ACTION",
        headline: "Buy a ticket.\nExplore sponsorship.\nMake a donation.",
        body: "Use the official event page",
        footer: "onecau.se/2026ccfgala",
        background: CGColor(red: 0.25, green: 0.20, blue: 0.17, alpha: 1)
    ),
    Scene(
        eyebrow: "CCF'S STATED MISSION",
        headline: "Support the work",
        body: "CCF says it funds locally based researchers, programs, and facilities.",
        footer: "No specific gift allocation or outcome is promised",
        background: CGColor(red: 0.13, green: 0.23, blue: 0.22, alpha: 1)
    ),
    Scene(
        eyebrow: "SOURCES + CONTEXT",
        headline: "Independent draft",
        body: "CCF gala: childrenscancerfoundation.org/events/gala\nCCF mission: childrenscancerfoundation.org/who-we-are/mission-and-history",
        footer: "Not an official event announcement. Not medical advice.",
        background: CGColor(red: 0.10, green: 0.19, blue: 0.18, alpha: 1)
    )
]

func drawText(
    _ text: String,
    in context: CGContext,
    rect: CGRect,
    size: CGFloat,
    color: CGColor,
    fontName: String = "AvenirNext-DemiBold"
) {
    let font = CTFontCreateWithName(fontName as CFString, size, nil)
    let attributes: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): color,
        NSAttributedString.Key(kCTKernAttributeName as String): 0.1
    ]
    let attributed = NSAttributedString(string: text, attributes: attributes)
    let setter = CTFramesetterCreateWithAttributedString(attributed)
    let path = CGPath(rect: rect, transform: nil)
    let frame = CTFramesetterCreateFrame(setter, CFRange(location: 0, length: attributed.length), path, nil)
    context.saveGState()
    context.textMatrix = .identity
    CTFrameDraw(frame, context)
    context.restoreGState()
}

func makeFrame(for scene: Scene, index: Int) throws -> CVPixelBuffer {
    var pixelBuffer: CVPixelBuffer?
    let attributes = [
        kCVPixelBufferCGImageCompatibilityKey: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey: true
    ] as CFDictionary
    let status = CVPixelBufferCreate(
        kCFAllocatorDefault,
        width,
        height,
        kCVPixelFormatType_32ARGB,
        attributes,
        &pixelBuffer
    )
    guard status == kCVReturnSuccess, let buffer = pixelBuffer else {
        throw NSError(domain: "GalaReel", code: Int(status))
    }
    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
    let bitmapInfo = CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.noneSkipFirst.rawValue
    guard let context = CGContext(
        data: CVPixelBufferGetBaseAddress(buffer),
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: bitmapInfo
    ) else {
        throw NSError(domain: "GalaReel", code: 2)
    }

    context.setFillColor(scene.background)
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.setFillColor(CGColor(red: 0.84, green: 0.67, blue: 0.39, alpha: 1))
    context.fill(CGRect(x: 58, y: 170, width: 7, height: 930))
    let ivory = CGColor(red: 0.97, green: 0.95, blue: 0.89, alpha: 1)
    let pale = CGColor(red: 0.85, green: 0.88, blue: 0.81, alpha: 1)
    let gold = CGColor(red: 0.91, green: 0.73, blue: 0.45, alpha: 1)
    drawText(scene.eyebrow, in: context, rect: CGRect(x: 88, y: 1055, width: 570, height: 54), size: 23, color: gold)
    drawText(scene.headline, in: context, rect: CGRect(x: 88, y: 680, width: 570, height: 330), size: 55, color: ivory)
    let bodySize: CGFloat = index == scenes.count - 1 ? 25 : 34
    drawText(scene.body, in: context, rect: CGRect(x: 88, y: 340, width: 560, height: 290), size: bodySize, color: pale, fontName: "AvenirNext-Regular")
    drawText(scene.footer, in: context, rect: CGRect(x: 88, y: 170, width: 560, height: 130), size: 22, color: ivory, fontName: "AvenirNext-Medium")

    let barWidth = CGFloat(width - 176) * CGFloat(index + 1) / CGFloat(scenes.count)
    context.setFillColor(gold)
    context.fill(CGRect(x: 88, y: 92, width: barWidth, height: 5))
    return buffer
}

func render() throws {
    try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    try? FileManager.default.removeItem(at: outputURL)

    let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
    let settings: [String: Any] = [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: width,
        AVVideoHeightKey: height,
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: 3_000_000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel
        ]
    ]
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
    input.expectsMediaDataInRealTime = false
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(
        assetWriterInput: input,
        sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
            kCVPixelBufferWidthKey as String: width,
            kCVPixelBufferHeightKey as String: height
        ]
    )
    guard writer.canAdd(input) else { throw NSError(domain: "GalaReel", code: 3) }
    writer.add(input)
    guard writer.startWriting() else { throw writer.error ?? NSError(domain: "GalaReel", code: 4) }
    writer.startSession(atSourceTime: .zero)

    var frameNumber: Int64 = 0
    for (sceneIndex, scene) in scenes.enumerated() {
        let frame = try makeFrame(for: scene, index: sceneIndex)
        for _ in 0..<(secondsPerScene * Int(fps)) {
            while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.002) }
            let time = CMTime(value: frameNumber, timescale: fps)
            guard adaptor.append(frame, withPresentationTime: time) else {
                throw writer.error ?? NSError(domain: "GalaReel", code: 5)
            }
            frameNumber += 1
        }
    }

    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else { throw writer.error ?? NSError(domain: "GalaReel", code: 6) }
    print("Rendered \(width)x\(height) vertical Reel (\(scenes.count * secondsPerScene)s): \(outputURL.path)")
}

do {
    try render()
} catch {
    fputs("Reel rendering failed: \(error)\n", stderr)
    exit(1)
}
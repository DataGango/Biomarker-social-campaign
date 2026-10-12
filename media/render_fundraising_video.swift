import AVFoundation
import AppKit
import CoreText
import CoreVideo
import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let audioURL = root.appendingPathComponent("fundraising-episode-01.m4a")
let silentURL = root.appendingPathComponent("fundraising-episode-01-silent.mov")
let outputURL = root.appendingPathComponent("fundraising-episode-01.mp4")
let width = 1280
let height = 720
let fps: Int32 = 12
let scenes: [(String, String, String, CGColor)] = [
    ("CHILDHOOD CANCER FUNDRAISING", "Start with purpose.", "Choose a verified nonprofit, hospital foundation, research program, or family-support organization.", CGColor(red: 0.12, green: 0.22, blue: 0.38, alpha: 1)),
    ("SET A TRANSPARENT GOAL", "Show the full picture.", "Separate the goal, event costs, platform fees, gross donations, and net funds delivered.", CGColor(red: 0.17, green: 0.32, blue: 0.29, alpha: 1)),
    ("REACH PEOPLE RESPECTFULLY", "Invite. Never pressure.", "Use opt-in community, workplace, school, civic, and grant audiences. Do not scrape private donor lists.", CGColor(red: 0.34, green: 0.22, blue: 0.25, alpha: 1)),
    ("CLOSE THE LOOP", "Report what happened.", "Thank supporters, reconcile costs, transfer the funds, and publish a clear campaign summary.", CGColor(red: 0.16, green: 0.28, blue: 0.39, alpha: 1))
]

func drawText(_ text: String, in context: CGContext, rect: CGRect, size: CGFloat, color: CGColor, font: String = "AvenirNext-DemiBold") {
    let ctFont = CTFontCreateWithName(font as CFString, size, nil)
    let attributes: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): ctFont,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): color,
        NSAttributedString.Key(kCTKernAttributeName as String): 0.2
    ]
    let string = NSAttributedString(string: text, attributes: attributes)
    let setter = CTFramesetterCreateWithAttributedString(string)
    let path = CGPath(rect: rect, transform: nil)
    let frame = CTFramesetterCreateFrame(setter, CFRange(location: 0, length: string.length), path, nil)
    context.saveGState()
    context.textMatrix = .identity
    CTFrameDraw(frame, context)
    context.restoreGState()
}

func makeFrame(_ scene: (String, String, String, CGColor)) throws -> CVPixelBuffer {
    var pixelBuffer: CVPixelBuffer?
    let attributes = [kCVPixelBufferCGImageCompatibilityKey: true, kCVPixelBufferCGBitmapContextCompatibilityKey: true] as CFDictionary
    let status = CVPixelBufferCreate(kCFAllocatorDefault, width, height, kCVPixelFormatType_32ARGB, attributes, &pixelBuffer)
    guard status == kCVReturnSuccess, let buffer = pixelBuffer else { throw NSError(domain: "FundraiserVideo", code: Int(status)) }
    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
    let bitmapInfo = CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.noneSkipFirst.rawValue
    guard let context = CGContext(data: CVPixelBufferGetBaseAddress(buffer), width: width, height: height, bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buffer), space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: bitmapInfo) else { throw NSError(domain: "FundraiserVideo", code: 2) }
    context.setFillColor(scene.3)
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.setFillColor(CGColor(red: 0.89, green: 0.69, blue: 0.37, alpha: 1))
    context.fill(CGRect(x: 72, y: 74, width: 8, height: 572))
    let white = CGColor(gray: 1, alpha: 1)
    let pale = CGColor(red: 0.86, green: 0.9, blue: 0.94, alpha: 1)
    drawText("CHILDHOOD CANCER FIELD GUIDE", in: context, rect: CGRect(x: 120, y: 594, width: 1000, height: 42), size: 25, color: pale)
    drawText(scene.0, in: context, rect: CGRect(x: 120, y: 480, width: 1050, height: 42), size: 25, color: CGColor(red: 0.98, green: 0.78, blue: 0.48, alpha: 1))
    drawText(scene.1, in: context, rect: CGRect(x: 120, y: 290, width: 1050, height: 150), size: 64, color: white)
    drawText(scene.2, in: context, rect: CGRect(x: 120, y: 130, width: 1030, height: 120), size: 30, color: pale, font: "AvenirNext-Regular")
    return buffer
}

func renderSilentVideo(duration: CMTime) async throws {
    try? FileManager.default.removeItem(at: silentURL)
    let writer = try AVAssetWriter(outputURL: silentURL, fileType: .mov)
    let settings: [String: Any] = [AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height]
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
    input.expectsMediaDataInRealTime = false
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB, kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height])
    guard writer.canAdd(input) else { throw NSError(domain: "FundraiserVideo", code: 3) }
    writer.add(input)
    writer.startWriting()
    writer.startSession(atSourceTime: .zero)
    let totalFrames = max(1, Int(CMTimeGetSeconds(duration) * Double(fps)))
    let framesPerScene = max(1, totalFrames / scenes.count)
    var frameNumber: Int64 = 0
    for (sceneIndex, scene) in scenes.enumerated() {
        let frame = try makeFrame(scene)
        let count = sceneIndex == scenes.count - 1 ? totalFrames - Int(frameNumber) : framesPerScene
        for _ in 0..<max(1, count) {
            while !input.isReadyForMoreMediaData { try await Task.sleep(nanoseconds: 2_000_000) }
            guard adaptor.append(frame, withPresentationTime: CMTime(value: frameNumber, timescale: fps)) else { throw writer.error ?? NSError(domain: "FundraiserVideo", code: 4) }
            frameNumber += 1
        }
    }
    input.markAsFinished()
    await writer.finishWriting()
    guard writer.status == .completed else { throw writer.error ?? NSError(domain: "FundraiserVideo", code: 5) }
}

func muxAudio() async throws {
    try? FileManager.default.removeItem(at: outputURL)
    let videoAsset = AVURLAsset(url: silentURL)
    let audioAsset = AVURLAsset(url: audioURL)
    let composition = AVMutableComposition()
    guard let videoSource = videoAsset.tracks(withMediaType: .video).first,
          let audioSource = audioAsset.tracks(withMediaType: .audio).first,
          let videoTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid),
          let audioTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) else { throw NSError(domain: "FundraiserVideo", code: 6) }
    let duration = min(videoAsset.duration, audioAsset.duration)
    try videoTrack.insertTimeRange(CMTimeRange(start: .zero, duration: duration), of: videoSource, at: .zero)
    try audioTrack.insertTimeRange(CMTimeRange(start: .zero, duration: duration), of: audioSource, at: .zero)
    guard let exporter = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality) else { throw NSError(domain: "FundraiserVideo", code: 7) }
    exporter.outputURL = outputURL
    exporter.outputFileType = .mp4
    let semaphore = DispatchSemaphore(value: 0)
    exporter.exportAsynchronously { semaphore.signal() }
    semaphore.wait()
    guard exporter.status == .completed else { throw exporter.error ?? NSError(domain: "FundraiserVideo", code: 8) }
    print("Created narrated video: \(outputURL.path)")
}

Task {
    do {
        let audioAsset = AVURLAsset(url: audioURL)
        try await renderSilentVideo(duration: audioAsset.duration)
        try await muxAudio()
        exit(0)
    } catch {
        fputs("Video generation failed: \(error)\n", stderr)
        exit(1)
    }
}
RunLoop.main.run()

import AVFoundation
import Foundation

func extractAudio(from inputPath: String, to outputPath: String) throws {
    let inputURL = URL(fileURLWithPath: inputPath)
    let outputURL = URL(fileURLWithPath: outputPath)
    let asset = AVURLAsset(url: inputURL)
    let semaphore = DispatchSemaphore(value: 0)
    var exportError: Error?

    guard let sourceTrack = asset.tracks(withMediaType: .audio).first else {
        throw NSError(domain: "EpisodeAudio", code: 1, userInfo: [NSLocalizedDescriptionKey: "No audio track found in \(inputPath)"])
    }
    let composition = AVMutableComposition()
    guard let destinationTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) else {
        throw NSError(domain: "EpisodeAudio", code: 2, userInfo: [NSLocalizedDescriptionKey: "Could not create audio track"])
    }
    try destinationTrack.insertTimeRange(CMTimeRange(start: .zero, duration: asset.duration), of: sourceTrack, at: .zero)
    try? FileManager.default.removeItem(at: outputURL)
    guard let exporter = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetAppleM4A) else {
        throw NSError(domain: "EpisodeAudio", code: 3, userInfo: [NSLocalizedDescriptionKey: "Could not create M4A exporter"])
    }
    exporter.outputURL = outputURL
    exporter.outputFileType = .m4a
    exporter.exportAsynchronously {
        if exporter.status != .completed {
            exportError = exporter.error ?? NSError(domain: "EpisodeAudio", code: 4, userInfo: [NSLocalizedDescriptionKey: "Audio export failed"])
        }
        semaphore.signal()
    }
    semaphore.wait()
    if let exportError { throw exportError }
    print("Wrote \(outputURL.path)")
}

for argument in CommandLine.arguments.dropFirst() {
    let pair = argument.split(separator: "=", maxSplits: 1).map(String.init)
    guard pair.count == 2 else {
        fputs("Expected INPUT=OUTPUT, got \(argument)\n", stderr)
        exit(2)
    }
    do {
        try extractAudio(from: pair[0], to: pair[1])
    } catch {
        fputs("\(error.localizedDescription)\n", stderr)
        exit(1)
    }
}

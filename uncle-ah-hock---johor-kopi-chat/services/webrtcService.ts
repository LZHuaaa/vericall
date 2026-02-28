/**
 * WebRTC Audio Bridge Service
 * Enables live peer-to-peer audio between the web app (scammer phone)
 * and Flutter app (victim phone) using Firebase Firestore for signaling.
 *
 * Flow:
 *   1. Web calls startCall() → captures mic, creates SDP offer, writes to Firestore
 *   2. Flutter reads offer → creates SDP answer → writes back
 *   3. Both exchange ICE candidates via Firestore subcollections
 *   4. P2P audio stream established
 */

import {
    addDoc,
    collection,
    deleteDoc,
    doc,
    Firestore,
    getDocs,
    getFirestore,
    onSnapshot,
    Unsubscribe,
    updateDoc
} from 'firebase/firestore';

// ─── Configuration ───────────────────────────────────────────────────────────

const ICE_SERVERS: RTCIceServer[] = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
];

const CALL_DOC_PATH = 'calls/current_demo';

/** Safely get Firestore instance, returns null if Firebase not initialized */
function safeGetFirestore(): Firestore | null {
    try {
        return getFirestore();
    } catch {
        console.warn('WebRTC: Firebase not initialized (missing VITE_FIREBASE_* env vars). WebRTC audio disabled.');
        return null;
    }
}

// ─── State ───────────────────────────────────────────────────────────────────

let peerConnection: RTCPeerConnection | null = null;
let localStream: MediaStream | null = null;
let remoteStream: MediaStream | null = null;

const unsubscribers: Unsubscribe[] = [];

// Callbacks for UI
let onRemoteStreamReady: ((stream: MediaStream) => void) | null = null;
let onConnectionStateChange: ((state: RTCPeerConnectionState) => void) | null = null;

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Start a WebRTC call as the offerer (web/scammer side).
 * Captures microphone, creates SDP offer, writes signaling to Firestore.
 */
export async function startWebRTCCall(): Promise<void> {
    console.log('📡 WebRTC: Starting call as offerer...');

    const db = safeGetFirestore();
    if (!db) throw new Error('Firestore not initialized – configure VITE_FIREBASE_* env vars');

    // Clean up any previous call
    await cleanupWebRTC();

    // 1. Capture local microphone
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        console.log('🎤 WebRTC: Microphone captured');
    } catch (err) {
        console.error('🎤 WebRTC: Failed to capture microphone:', err);
        throw new Error('Microphone access denied');
    }

    // 2. Create peer connection
    peerConnection = new RTCPeerConnection({ iceServers: ICE_SERVERS });

    // 3. Add local audio tracks to the connection
    localStream.getTracks().forEach((track) => {
        peerConnection!.addTrack(track, localStream!);
    });

    // 4. Handle incoming remote stream (audio from Flutter)
    remoteStream = new MediaStream();
    peerConnection.ontrack = (event) => {
        console.log('🔊 WebRTC: Remote track received', event.track.kind);
        event.streams[0]?.getTracks().forEach((track) => {
            remoteStream!.addTrack(track);
        });
        if (onRemoteStreamReady) {
            onRemoteStreamReady(remoteStream!);
        }
        // Auto-play remote audio
        playRemoteAudio(remoteStream!);
    };

    // 5. Connection state monitoring
    peerConnection.onconnectionstatechange = () => {
        const state = peerConnection?.connectionState || 'closed';
        console.log(`📡 WebRTC: Connection state → ${state}`);
        if (onConnectionStateChange) {
            onConnectionStateChange(state as RTCPeerConnectionState);
        }
    };

    peerConnection.oniceconnectionstatechange = () => {
        console.log(`📡 WebRTC: ICE connection state → ${peerConnection?.iceConnectionState}`);
    };

    // 6. Collect ICE candidates and write to Firestore
    const iceCandidatesRef = collection(db, 'calls', 'current_demo', 'ice_web');
    peerConnection.onicecandidate = async (event) => {
        if (event.candidate) {
            try {
                await addDoc(iceCandidatesRef, event.candidate.toJSON());
            } catch (err) {
                console.warn('WebRTC: Failed to write ICE candidate:', err);
            }
        }
    };

    // 7. Create SDP offer
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    console.log('📡 WebRTC: SDP offer created');

    // 8. Write offer to Firestore call document
    const callDocRef = doc(db, CALL_DOC_PATH);
    await updateDoc(callDocRef, {
        webRtcOffer: {
            type: offer.type,
            sdp: offer.sdp,
        },
    });
    console.log('📡 WebRTC: Offer written to Firestore');

    // 9. Listen for SDP answer from Flutter
    const answerUnsub = onSnapshot(callDocRef, (snapshot) => {
        const data = snapshot.data();
        if (!data?.webRtcAnswer || !peerConnection) return;
        if (peerConnection.currentRemoteDescription) return; // Already set

        const answer = new RTCSessionDescription(data.webRtcAnswer);
        peerConnection.setRemoteDescription(answer).then(() => {
            console.log('📡 WebRTC: Remote SDP answer set');
        }).catch((err) => {
            console.error('WebRTC: Failed to set remote description:', err);
        });
    });
    unsubscribers.push(answerUnsub);

    // 10. Listen for ICE candidates from Flutter
    const mobileIceRef = collection(db, 'calls', 'current_demo', 'ice_mobile');
    const mobileIceUnsub = onSnapshot(mobileIceRef, (snapshot) => {
        snapshot.docChanges().forEach((change) => {
            if (change.type === 'added' && peerConnection) {
                const candidateData = change.doc.data();
                const candidate = new RTCIceCandidate(candidateData);
                peerConnection.addIceCandidate(candidate).catch((err) => {
                    console.warn('WebRTC: Failed to add remote ICE candidate:', err);
                });
            }
        });
    });
    unsubscribers.push(mobileIceUnsub);

    console.log('📡 WebRTC: Signaling active, waiting for Flutter answer...');
}

/**
 * Clean up WebRTC resources and Firestore signaling data.
 */
export async function cleanupWebRTC(): Promise<void> {
    console.log('📡 WebRTC: Cleaning up...');

    // Unsubscribe all listeners
    unsubscribers.forEach((unsub) => unsub());
    unsubscribers.length = 0;

    // Close peer connection
    if (peerConnection) {
        peerConnection.ontrack = null;
        peerConnection.onicecandidate = null;
        peerConnection.onconnectionstatechange = null;
        peerConnection.oniceconnectionstatechange = null;
        peerConnection.close();
        peerConnection = null;
    }

    // Stop local media
    if (localStream) {
        localStream.getTracks().forEach((track) => track.stop());
        localStream = null;
    }

    remoteStream = null;

    // Remove audio element
    const existingAudio = document.getElementById('webrtc-remote-audio') as HTMLAudioElement;
    if (existingAudio) {
        existingAudio.pause();
        existingAudio.srcObject = null;
        existingAudio.remove();
    }

    // Clean up Firestore signaling data
    try {
        const db = safeGetFirestore();
        if (db) {
            // Remove WebRTC offer/answer from call doc
            const callDocRef = doc(db, CALL_DOC_PATH);
            await updateDoc(callDocRef, {
                webRtcOffer: null,
                webRtcAnswer: null,
            }).catch(() => { }); // Ignore if doc doesn't exist

            // Delete ICE candidate subcollections
            await deleteIceCollection(db, 'calls', 'current_demo', 'ice_web');
            await deleteIceCollection(db, 'calls', 'current_demo', 'ice_mobile');
        }
    } catch (err) {
        console.warn('WebRTC: Cleanup Firestore error (non-fatal):', err);
    }

    console.log('📡 WebRTC: Cleanup complete');
}

/**
 * Set callback for when remote audio stream is ready
 */
export function setOnRemoteStreamReady(callback: (stream: MediaStream) => void): void {
    onRemoteStreamReady = callback;
}

/**
 * Set callback for connection state changes
 */
export function setOnConnectionStateChange(callback: (state: RTCPeerConnectionState) => void): void {
    onConnectionStateChange = callback;
}

/**
 * Check if WebRTC is currently active
 */
export function isWebRTCActive(): boolean {
    return peerConnection !== null && peerConnection.connectionState !== 'closed';
}

// ─── Internal Helpers ────────────────────────────────────────────────────────

/**
 * Play remote audio stream through an invisible audio element
 */
function playRemoteAudio(stream: MediaStream): void {
    let audioEl = document.getElementById('webrtc-remote-audio') as HTMLAudioElement;
    if (!audioEl) {
        audioEl = document.createElement('audio');
        audioEl.id = 'webrtc-remote-audio';
        audioEl.autoplay = true;
        audioEl.style.display = 'none';
        document.body.appendChild(audioEl);
    }
    audioEl.srcObject = stream;
    audioEl.play().catch((err) => {
        console.warn('WebRTC: Auto-play blocked, user interaction needed:', err);
    });
}

/**
 * Delete all documents in a Firestore subcollection
 */
async function deleteIceCollection(
    db: ReturnType<typeof getFirestore>,
    collectionPath: string,
    docPath: string,
    subcollectionPath: string,
): Promise<void> {
    try {
        const colRef = collection(db, collectionPath, docPath, subcollectionPath);
        const snapshot = await getDocs(colRef);
        const deletePromises = snapshot.docs.map((d) => deleteDoc(d.ref));
        await Promise.all(deletePromises);
    } catch (err) {
        // Non-fatal: collection may not exist
    }
}

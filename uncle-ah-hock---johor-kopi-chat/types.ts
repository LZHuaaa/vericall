/**
 * Types Module (Legacy Compatibility)
 * Re-exports types from the new modular structure
 */

// Re-export types (using 'export type' for isolatedModules compatibility)
export type {
  AudioVisualizerProps,
  BotDetectionStatus,
  CallMetrics,
  LogMessage,
  ThreatAssessment,
  ScamEvidence,
  ScamPattern
} from './services/types/scamTypes';

// Re-export values (enums, constants)
export {
  ConnectionState,
  PHONETICS,
  SCAM_PATTERNS,
  SCAM_SCORING
} from './services/types/scamTypes';

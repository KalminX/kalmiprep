/**
 * KalmiPrep Auth Fixtures Helper
 *
 * Provides mock sessions, CSRF resolution, and authenticated test contexts
 * for student and teacher roles.
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

const TEST_USERS = {
  student: {
    username: process.env.TEST_STUDENT_USER || 'student_test',
    password: process.env.TEST_STUDENT_PASSWORD || 'KalmiPass123!',
    role: 'student',
    profile: {
      exam_target: 'JAMB',
      department: 'Science'
    }
  },
  teacher: {
    username: process.env.TEST_TEACHER_USER || 'teacher_test',
    password: process.env.TEST_TEACHER_PASSWORD || 'KalmiPass123!',
    role: 'teacher',
    is_verified: true,
    bank_account_configured: true
  },
  staff: {
    username: process.env.TEST_STAFF_USER || 'staff_test',
    password: process.env.TEST_STAFF_PASSWORD || 'KalmiPass123!',
    role: 'staff'
  }
};

/**
 * Creates authenticated cookies or headers for test requests.
 */
function getAuthHeaders(role = 'student', token = 'mock-session-token') {
  return {
    'Cookie': `sessionid=${token}; role=${role}`,
    'X-CSRFToken': 'test-csrf-token',
    'User-Agent': 'KalmiPrepBlueprintHarness/1.0'
  };
}

module.exports = {
  BASE_URL,
  TEST_USERS,
  getAuthHeaders
};

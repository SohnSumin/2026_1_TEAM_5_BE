import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

const String baseApiUrl = "http://127.0.0.1:8000/api";

class SeenearService {
  String? _accessToken;
  Map<String, dynamic>? _myProfile;

  // --- [Auth & Profile] ---
  Future<void> requestOtp(String phoneNumber) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/otp/request'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber}),
    );
    if (response.statusCode == 200) {
      print("OTP 발송 성공: ${jsonDecode(response.body)['debug_otp']}");
    } else {
      throw Exception("OTP 요청 실패: ${response.body}");
    }
  }

  Future<Map<String, dynamic>> login(String phoneNumber, String otpCode) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber, 'otp_code': otpCode}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _accessToken = data['access_token'];
      // 로그인 직후 프로필 정보를 캐싱하여 'admin' 여부 확인에 사용
      _myProfile = await getMyProfile();
      return data;
    } else {
      throw Exception("로그인 실패: ${response.body}");
    }
  }

  Future<Map<String, dynamic>> getMyProfile() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/auth/me'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    return jsonDecode(response.body);
  }

  // --- [Report Methods] ---

  /// 1. 새로운 신고 생성 (일반 유저)
  Future<Map<String, dynamic>> createReport({
    required String reportedUserId,
    required List<String> reasons,
    required String description,
  }) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/reports'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken'
      },
      body: jsonEncode({
        'reported_user_id': reportedUserId,
        'reason': reasons,
        'description': description,
      }),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("신고 생성 실패 (${response.statusCode}): ${response.body}");
  }

  /// 2. 모든 신고 내역 조회 (Admin 전용)
  Future<List<dynamic>> getAllReports() async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/reports/all_reports'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("신고 조회 실패 (권한 부족 가능성): ${response.body}");
  }

  /// 3. 신고 상태 변경 (Admin 전용)
  Future<Map<String, dynamic>> updateReportStatus(
      String reportId, String status) async {
    final response = await http.patch(
      Uri.parse('$baseApiUrl/reports/$reportId/status?status=$status'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("상태 변경 실패: ${response.body}");
  }

  /// 4. 신고 삭제 (Admin 전용)
  Future<void> deleteReport(String reportId) async {
    final response = await http.delete(
      Uri.parse('$baseApiUrl/reports/$reportId'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    if (response.statusCode != 200)
      throw Exception("신고 삭제 실패: ${response.body}");
  }

  Map<String, dynamic>? get myProfile => _myProfile;
  String? get nickname => _myProfile?['nickname'] ?? _myProfile?['name'];
}

void main() async {
  final service = SeenearService();
  print("=== SEENEAR 신고 시스템 & 권한 테스트 클라이언트 ===");

  while (true) {
    try {
      print("\n[1] 로그인 (Admin/일반 테스트) [2] 신고하기 [3] [관리자] 신고관리 [q] 종료");
      final choice = getInput("선택");

      if (choice == 'q') break;

      if (choice == '1') {
        final phone = getInput("전화번호");
        await service.requestOtp(phone);
        final otp = getInput("인증번호 (테스트: 123456)");
        await service.login(phone, otp);
        print("로그인 완료! 현재 접속자: ${service.nickname}");
      } else if (choice == '2') {
        print("\n--- 새로운 신고 생성 ---");
        final targetId = getInput("신고할 유저 ID (UUID)");
        print("신고 사유를 입력하세요 (쉼표로 구분, 예: NO_SHOW, RUDENESS)");
        final reasons = getInput("사유").split(',').map((e) => e.trim()).toList();
        print("추가 설명이 있으면 입력하세요 (없으면 엔터)");
        final description = getInput("설명");

        final res = await service.createReport(
            reportedUserId: targetId,
            reasons: reasons,
            description: description);
        print("✅ 신고 접수 완료! (신고 ID: ${res['report_id']})");
      } else if (choice == '3') {
        print("\n--- [관리자 전용] 신고 내역 관리 ---");
        // 이 부분에서 admin이 아니면 백엔드에서 403 에러를 던지는지 확인 가능
        final reports = await service.getAllReports();

        if (reports.isEmpty) {
          print("접수된 신고가 없습니다.");
          continue;
        }

        for (var r in reports) {
          print("----------------------------------");
          print("ID: ${r['report_id']} | 상태: ${r['status']}");
          print(
              "신고자: ${r['reporter_user_id']} -> 피신고자: ${r['reported_user_id']}");
          print("사유: ${r['reason']}");
          print("설명: ${r['description']}");
          print("----------------------------------");
        }

        print("\n[1] 상태변경 [2] 삭제 [엔터] 뒤로가기");
        final op = getInput("선택");
        if (op == '1') {
          final id = getInput("변경할 신고 ID");
          final status = getInput("새 상태 (RESOLVED / REJECTED)");
          await service.updateReportStatus(id, status);
          print("✅ 상태 변경 완료!");
        } else if (op == '2') {
          final id = getInput("삭제할 신고 ID");
          await service.deleteReport(id);
          print("✅ 삭제 완료!");
        }
      }
    } catch (e) {
      print("\n❌ 에러 발생: $e");
    }
  }
}

String getInput(String prompt) {
  stdout.write('$prompt: ');
  return stdin.readLineSync(encoding: utf8) ?? "";
}

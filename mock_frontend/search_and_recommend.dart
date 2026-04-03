import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class SeenearService {
  final String baseApiUrl = "http://127.0.0.1:8000/api";
  String? _accessToken;
  String? role;

  Map<String, String> _getHeaders() {
    final headers = {'Content-Type': 'application/json'};
    if (_accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    return headers;
  }

  // 1. 로그인 및 역할 저장
  Future<Map<String, dynamic>> login(String phone, String otp) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/login'),
      headers: _getHeaders(),
      body: jsonEncode({'phone_number': phone, 'otp_code': otp}),
    );
    final data = jsonDecode(response.body);
    if (data['access_token'] != "not_issued") {
      _accessToken = data['access_token'];
      role = data['role']; // SENIOR 또는 REQUESTER 저장
    }
    return data;
  }

  // 2. [시니어용] 맞춤 공고 검색 (내 위치 기반 추천)
  Future<List<dynamic>> searchJobsForSenior({int rangeM = 15000}) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/search/jobs?range_m=$rangeM'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("공고 검색 실패: ${response.body}");
  }

  // 3. [요청자용] 특정 공고에 적합한 주변 시니어 검색
  Future<List<dynamic>> searchSeniorsForJob(String postId,
      {int rangeM = 15000}) async {
    final response = await http.get(
      Uri.parse('$baseApiUrl/search/seniors/$postId?range_m=$rangeM'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception("시니어 검색 실패: ${response.body}");
  }
}

void main() async {
  final service = SeenearService();

  print("=== [Seenear 통합 검색 시스템 로그인] ===");
  stdout.write("전화번호(010-XXXX-XXXX): ");
  String phone = stdin.readLineSync(encoding: utf8) ?? "";

  // 로그인 수행 (OTP 123456 고정)
  var loginRes = await service.login(phone, "123456");

  if (!loginRes['is_registered']) {
    print("❌ 가입되지 않은 번호입니다. 가입 먼저 진행해주세요.");
    return;
  }

  String userRole = service.role ?? "";
  print("✅ 로그인 성공! 현재 역할: $userRole\n");

  if (userRole == "SENIOR") {
    // [시니어 시나리오]
    print("--- [시니어 맞춤 공고 검색] ---");
    stdout.write("검색 반경 입력(미터 단위, 기본 15000): ");
    int range = int.tryParse(stdin.readLineSync() ?? "15000") ?? 15000;

    try {
      var jobs = await service.searchJobsForSenior(rangeM: range);
      print("\n📍 내 활동 거점 근처의 공고 검색 결과 (${jobs.length}건):");
      for (var job in jobs) {
        print(
            "- [${job['status']}] ${job['title']} | 보수: ${job['reward']}원 | 위치: ${job['location_name']}");
      }
    } catch (e) {
      print("❌ 검색 중 오류 발생: $e");
    }
  } else if (userRole == "REQUESTER") {
    // [요청자 시나리오]
    print("--- [공고별 추천 시니어 검색] ---");
    // 실제로는 내 공고 목록을 가져와서 선택해야 하지만, 시연용으로 ID 직접 입력 유도
    stdout.write("검색할 내 공고 ID(UUID) 입력: ");
    String postId = stdin.readLineSync() ?? "";

    if (postId.isEmpty) {
      print("💡 팁: /api/jobs/my 엔드포인트에서 공고 ID를 확인하세요.");
      return;
    }

    stdout.write("검색 반경 입력(미터 단위, 기본 15000): ");
    int range = int.tryParse(stdin.readLineSync() ?? "15000") ?? 15000;

    try {
      var seniors = await service.searchSeniorsForJob(postId, rangeM: range);
      print("\n📍 해당 공고 근처에 계시는 시니어 추천 결과 (${seniors.length}명):");
      for (var s in seniors) {
        print(
            "- [${s['gender']}] ${s['name']}님 | 관심태그: ${s['sub_tags']} | 자기소개: ${s['bio_summary']}");
      }
    } catch (e) {
      print("❌ 검색 중 오류 발생: $e");
    }
  }
}

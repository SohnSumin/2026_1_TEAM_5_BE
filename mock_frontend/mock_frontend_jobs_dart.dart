import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:io';

class SeenearService {
  final String baseApiUrl = "http://127.0.0.1:8000/api";
  String? _accessToken;

  Map<String, String> _getHeaders() {
    final headers = {'Content-Type': 'application/json'};
    if (_accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    return headers;
  }

  // 1. 로그인 (토큰 획득)
  Future<void> login(String phone, String otp) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/auth/login'),
      headers: _getHeaders(),
      body: jsonEncode({'phone_number': phone, 'otp_code': otp}),
    );
    final data = jsonDecode(response.body);
    if (data['access_token'] != "not_issued") {
      _accessToken = data['access_token'];
    }
  }

  // 2. [직접 선택용] AI 태그 추천 받기
  Future<Map<String, dynamic>> getRecommendedTags(
      String title, String content) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/jobs/recommend-tags'), // 백엔드 오타 반영
      headers: _getHeaders(),
      body: jsonEncode({'title': title, 'content': content}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception("태그 추천 실패");
  }

  // 3. [최종 등록] 사용자가 선택한 태그를 포함하여 등록
  Future<Map<String, dynamic>> createJob({
    required String title,
    required String content,
    required List<String> selectedMainTags,
    required List<String> selectedSubTags,
  }) async {
    final response = await http.post(
      Uri.parse('$baseApiUrl/jobs'),
      headers: _getHeaders(),
      body: jsonEncode({
        'title': title,
        'content': content,
        'main_tags': selectedMainTags,
        'sub_tags': selectedSubTags,
        'job_date': "2026-04-10",
        'start_time': "15:00:00",
        'location_name': "강남역 2번 출구",
        'latitude': 37.4979,
        'longitude': 127.0276,
        'reward': 15000,
        'image_urls': [],
      }),
    );
    return jsonDecode(response.body);
  }
}

void main() async {
  final service = SeenearService();

  print("=== [로그인 단계] ===");
  stdout.write("전화번호 입력 (010-XXXX-XXXX): ");
  String phone = stdin.readLineSync()!;

  await service.login(phone, "123456");
  print("✅ 로그인 성공 및 토큰 확보\n");

  print("=== [공고 작성 단계] ===");
  stdout.write("공고 제목: ");
  String title = stdin.readLineSync()!;
  stdout.write("상세 내용: ");
  String content = stdin.readLineSync()!;

  print("\n--- AI가 태그를 분석 중입니다... ---");
  var aiTags = await service.getRecommendedTags(title, content);

  List<String> recommendedMain =
      List<String>.from(aiTags['recommended_main_tags']);
  List<String> recommendedSub =
      List<String>.from(aiTags['recommended_sub_tags']);

  print("\n[AI 추천 메인 카테고리]: $recommendedMain");
  print("[AI 추천 상세 키워드]: $recommendedSub");

  // 사용자가 직접 선택하는 과정 시뮬레이션
  print("\n--- [태그 선택 단계] ---");
  print("1. AI 추천 태그를 그대로 사용하시겠습니까? (y/n)");
  String choice = stdin.readLineSync()!;

  List<String> finalMain = [];
  List<String> finalSub = [];

  if (choice.toLowerCase() == 'y') {
    finalMain = recommendedMain;
    finalSub = recommendedSub;
  } else {
    // 직접 입력 시나리오 (예시 데이터)
    finalMain = ["가사 및 환경 관리"];
    finalSub = ["반찬 만들기"];
    print("직접 선택 완료: $finalMain / $finalSub");
  }

  print("\n=== [최종 등록 단계] ===");
  try {
    var result = await service.createJob(
      title: title,
      content: content,
      selectedMainTags: finalMain,
      selectedSubTags: finalSub,
    );
    print("🚀 공고 등록이 완료되었습니다!");
    print("공고 ID: ${result['post_id']}");
    print("등록된 태그: ${result['main_tags']} / ${result['sub_tags']}");
  } catch (e) {
    print("❌ 등록 실패: $e");
  }
}

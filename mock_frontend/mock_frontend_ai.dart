import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;

class SeeNearAiTestClient {
  final String baseUrl = "http://127.0.0.1:8000/api";
  String? seniorToken;
  String? requesterToken;

  // 전화번호 하이픈 필수 규칙 적용 (010-XXXX-XXXX)
  String get generateRandomPhone {
    var n1 = (Random().nextInt(8999) + 1000).toString();
    var n2 = (Random().nextInt(8999) + 1000).toString();
    return "010-$n1-$n2";
  }

  // [공통] 로그인 함수
  Future<String?> login(String phoneNumber) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone_number': phoneNumber, 'otp_code': '123456'}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['access_token'];
    }
    return null;
  }

  // [SCENARIO 1] 시니어 가입 (AI 태그 추천 포함)
  Future<void> runSeniorTest() async {
    print("\n--- [시니어 테스트] 시작 ---");
    final phone = generateRandomPhone;
    const bio = "요리 잘하고 복지관에서 근무한 경험이 있어요. 산책도 좋아하거든유";

    // 1. AI 태그 추천
    final recRes = await http.post(
      Uri.parse('$baseUrl/auth/tags/recommend'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'bio_summary': bio}),
    );
    var recommended = jsonDecode(recRes.body)['recommended_tags'];
    print("🤖 AI 추천 시니어 태그: $recommended");

    // 2. 가입 (하이픈 포함된 번호 사용)
    final res = await http.post(
      Uri.parse('$baseUrl/auth/signup/senior'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phone,
        'name': '김시니어',
        'gender': 'FEMALE',
        'birth_year': 1962,
        'bio_summary': bio,
        'tags': recommended,
        'auth_code': 'SEMO-2026',
        'locations': [
          {
            'location_name': '회기역',
            'latitude': 37.589,
            'longitude': 127.057,
            'is_primary': true
          }
        ],
        'profile_icon': 'GRANNY_1'
      }),
    );
    print("🎉 시니어 가입(${phone}): ${res.statusCode == 200 ? "성공" : res.body}");
    seniorToken = await login(phone);
  }

  // [SCENARIO 2] 요청자 가입 및 공고 (AI 카테고리 포함)
  Future<void> runRequesterTest() async {
    print("\n--- [요청자 테스트] 시작 ---");
    final phone = generateRandomPhone;

    // 1. 요청자 가입
    final regRes = await http.post(
      Uri.parse('$baseUrl/auth/signup/req'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone_number': phone,
        'nickname': '수민요청자',
        'gender': 'MALE',
        'birth_year': 1995,
      }),
    );
    print(
        "🎉 요청자 가입(${phone}): ${regRes.statusCode == 200 ? "성공" : regRes.body}");
    requesterToken = await login(phone);

    // 2. 공고 태그 추천 및 등록
    const content = "내일 오후에 병원 동행해주실 분 찾습니다. 거동이 조금 불편하셔서 부축이 필요해요.";
    final recRes = await http.post(
      Uri.parse('$baseUrl/jobs/recommend-tag'),
      headers: {
        'Authorization': 'Bearer $requesterToken',
        'Content-Type': 'application/json'
      },
      body: jsonEncode({'content': content}),
    );
    String aiTag = jsonDecode(recRes.body)['recommended_tag'];
    print("🤖 AI 추천 공고 태그: $aiTag");

    final jobRes = await http.post(
      Uri.parse('$baseUrl/jobs'),
      headers: {
        'Authorization': 'Bearer $requesterToken',
        'Content-Type': 'application/json'
      },
      body: jsonEncode({
        'title': '병원 동행 부탁드립니다',
        'content': content,
        'category_tag': aiTag,
        'job_date': '2026-04-10',
        'location_name': '경희의료원',
        'latitude': 37.590,
        'longitude': 127.050,
        'start_time': '10:00',
        'reward': 20000,
        'image_urls': []
      }),
    );
    print("📝 공고 등록: ${jobRes.statusCode == 200 ? "성공" : jobRes.body}");
  }
}

void main() async {
  final client = SeeNearAiTestClient();

  // 1. 시니어 가입 테스트
  await client.runSeniorTest();

  print("\n⏳ 쿼터 초기화를 위해 15초간 대기합니다... (429 방지)");
  await Future.delayed(Duration(seconds: 15)); // 여기서 숨을 고릅니다.

  // 2. 요청자 공고 테스트
  await client.runRequesterTest();
}

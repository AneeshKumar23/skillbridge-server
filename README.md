
## 📡 API Reference

SkillBridge provides a RESTful API for managing users, prompts, outputs, and AI-generated content. Below is a summary of available endpoints.

---

### 👤 User Management

#### ➕ Create a User

```http
POST /users/
```

**Body Parameters:**

| Parameter    | Type     | Description                   |
| ------------ | -------- | ----------------------------- |
| `email`      | `string` | **Required**. User email      |
| `first_name` | `string` | **Required**. User first name |
| `last_name`  | `string` | **Optional**. User last name  |

---

#### 📄 Get a User

```http
GET /users/{user_id}
```

**Path Parameters:**

| Parameter | Type     | Description                  |
| --------- | -------- | ---------------------------- |
| `user_id` | `string` | **Required**. ID of the user |

---

### 💬 Prompt Management

#### ➕ Add Prompt

```http
POST /prompts/{user_id}
```

**Query Parameters:**

| Parameter | Type     | Description               |
| --------- | -------- | ------------------------- |
| `prompt`  | `string` | **Required**. Prompt text |

---

#### 📄 Get Prompts

```http
GET /prompts/{user_id}
```

**Path Parameters:**

| Parameter | Type     | Description                  |
| --------- | -------- | ---------------------------- |
| `user_id` | `string` | **Required**. ID of the user |

---

### 📤 Output Management

#### ➕ Add Output

```http
POST /outputs/{user_id}
```

**Query Parameters:**

| Parameter | Type     | Description                  |
| --------- | -------- | ---------------------------- |
| `output`  | `string` | **Required**. Output content |

---

#### 📄 Get Outputs

```http
GET /outputs/{user_id}
```

**Path Parameters:**

| Parameter | Type     | Description                  |
| --------- | -------- | ---------------------------- |
| `user_id` | `string` | **Required**. ID of the user |

---

### 🧠 AI-Generated Content

#### 📰 Generate Article Links

```http
POST /api/generate_article
```

**Query Parameters:**

| Parameter | Type     | Description                |
| --------- | -------- | -------------------------- |
| `prompt`  | `string` | **Required**. Prompt input |

---

#### 📺 Generate YouTube Content Links

```http
POST /api/generate_youtube_content
```

**Query Parameters:**

| Parameter | Type     | Description                |
| --------- | -------- | -------------------------- |
| `prompt`  | `string` | **Required**. Prompt input |

---

#### 🧾 Generate Certificate

```http
POST /certificate/{user_id}
```

**Path Parameters:**

| Parameter | Type     | Description                  |
| --------- | -------- | ---------------------------- |
| `user_id` | `string` | **Required**. ID of the user |

Returns a URL to a generated certificate.

---

#### 📚 Generate Custom Content (Gemini)

```http
POST /api/generate_content
```

**Query Parameters:**

| Parameter | Type     | Description                |
| --------- | -------- | -------------------------- |
| `prompt`  | `string` | **Required**. Prompt input |



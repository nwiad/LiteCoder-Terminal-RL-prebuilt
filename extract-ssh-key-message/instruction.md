## Task: Extract Hidden Message from SSH Key

A hidden message has been embedded inside an RSA private key file using steganographic techniques. The key file remains valid and functional. Your task is to extract and reveal the hidden message.

**Technical Requirements:**
- Language: Python 3.x or Bash
- Input file: `/app/private_key.pem` (RSA private key with hidden message)
- Output file: `/app/extracted_message.txt` (plain text containing the extracted message)

**Input Specification:**
- The input file is a valid RSA private key in PEM format
- A message is hidden within the key file using steganographic techniques
- The key structure remains intact and functional

**Output Specification:**
- Write the extracted hidden message to `/app/extracted_message.txt`
- The output should contain only the extracted message text (no additional formatting, headers, or metadata)
- Remove any trailing whitespace or newlines

**Task Requirements:**
1. Analyze the RSA private key file structure
2. Identify the steganographic technique used to conceal the message
3. Extract the hidden message using appropriate methods or tools
4. Save the extracted message to the output file

**Edge Cases:**
- The message may be encoded or obfuscated
- Multiple steganographic layers may be present
- The extraction method should not corrupt the original key file

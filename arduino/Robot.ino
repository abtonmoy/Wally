#include <Arduino.h>
#include <Encoder.h>
#define PI 3.1416f
//The approximate number of steps in a full 2pi rotation. 
#define ENCODER_STEPS_PER_ROTATION 3000
#include "motor.h"
#include "bot.h"








// Motor pins

//back right
const int DIR_PIN_1 = 13; 
const int PWM_PIN_1 = 12; 
const int ENCA_1 = 18;
const int ENCB_1 = 22;

//front right
const int DIR_PIN_2 = 10; 
const int PWM_PIN_2 = 11; 
const int ENCA_2 = 23;
const int ENCB_2 = 19;

//front left
const int DIR_PIN_3 = 9;
const int PWM_PIN_3 = 8;
const int ENCA_3 = 24;
const int ENCB_3 = 20;

//back left
const int DIR_PIN_4 = 7;
const int PWM_PIN_4 = 6;
const int ENCA_4 = 25;
const int ENCB_4 = 21;


// Initialize motors






Motor* front_right;
Motor* front_left;
Motor* back_right;
Motor* back_left;

Bot* bot;


// HC-SR04 sensor pins
const int TRIGGER_PIN_1 = 2; // Trigger pin for Left Sonar
const int ECHO_PIN_1 = 3;    // Echo pin for Left Sonar
const int TRIGGER_PIN_2 = 4; // Trigger pin for Right Sonar
const int ECHO_PIN_2 = 5;    // Echo pin for Right Sonar



void setup() {

    Serial.begin(9600);
    
    back_right = new Motor(DIR_PIN_1, PWM_PIN_1, HIGH, 100.0f, ENCA_1, ENCB_1, 1);
    front_right = new Motor(DIR_PIN_2, PWM_PIN_2, HIGH, 100.0f, ENCA_2, ENCB_2, 1);

    front_left = new Motor(DIR_PIN_3, PWM_PIN_3, HIGH,  100.0f, ENCA_3, ENCB_3, 1);
    back_left = new Motor(DIR_PIN_4, PWM_PIN_4, HIGH, 100.0f, ENCA_4, ENCB_4, 1);

    bot = new Bot(front_right, back_right, front_left, back_left, 0.46, 0.05);

}


#define PRINT_DEBUG(var) Serial.print(#var " is: "); Serial.println(var)


enum COMMANDS {
  MOVE_WHEEL,
  TURN_WHILE_MOVING,
  TURN_BOT_INPLACE,
  DRIVE_STRAIGHT,
  MOVE_FORWARD_M_METERS,
  REVERSE
};

struct packet {
  char command;
  char specifier;
  float f1;
  float f2;
  float f3;
};


struct packet curr_packet;

void execute_command(struct packet* curr_packet) {

  switch(curr_packet->command) {
    case (char) MOVE_WHEEL:
    {
      switch(curr_packet->specifier) {
        case 0:
          back_right->turn_by_angle(curr_packet->f1, curr_packet->f2);
        break;
        case 1: 
          front_right->turn_by_angle(curr_packet->f1, curr_packet->f2);
        break;
        case 2: 
          front_left->turn_by_angle(curr_packet->f1, curr_packet->f2);
        break;
        case 3: 
          back_left->turn_by_angle(curr_packet->f1, curr_packet->f2);
        break;
      }
    } break;

    case (char) TURN_WHILE_MOVING:
    {
      bot->turn_while_moving(curr_packet->f1, curr_packet->f2);
    } break;

    case (char) TURN_BOT_INPLACE:
    {
      bot->turn_inplace(curr_packet->f1, curr_packet->f2);
    } break;

    case (char) DRIVE_STRAIGHT:
    {
      bot->drive_straight(curr_packet->f1);
    } break;

    case (char) MOVE_FORWARD_M_METERS:
    {
      bot->drive_m_meters(curr_packet->f1, curr_packet->f2);
    } break;

    case (char) REVERSE:
    {
      bot->reverse(curr_packet->f1);
    } break;

   

  }


}

void loop() {


    if (Serial.available() >= sizeof(struct packet)) {
      Serial.readBytes((char*)&curr_packet, sizeof(curr_packet));
      execute_command(&curr_packet);
    }
  

  front_right->update();  
  front_left->update();
  back_left->update();
  back_right->update();
}


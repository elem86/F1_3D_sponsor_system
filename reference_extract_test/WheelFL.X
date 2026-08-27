xof 0302txt 0064
//
// DirectX file: C:\3DSMAX\meshes\WheelFL.X
//
// Converted by the PolyTrans geometry converter from Okino Computer Graphics, Inc.
// Date/time of export: 11/04/1998 16:21:30
//
// Bounding box of geometry = (-0.119338,-0.230463,-0.230463) to (0.119338,0.230463,0.230463).


template Header {
 <3D82AB43-62DA-11cf-AB39-0020AF71E433>
 WORD major;
 WORD minor;
 DWORD flags;
}

template Vector {
 <3D82AB5E-62DA-11cf-AB39-0020AF71E433>
 FLOAT x;
 FLOAT y;
 FLOAT z;
}

template Coords2d {
 <F6F23F44-7686-11cf-8F52-0040333594A3>
 FLOAT u;
 FLOAT v;
}

template Matrix4x4 {
 <F6F23F45-7686-11cf-8F52-0040333594A3>
 array FLOAT matrix[16];
}

template ColorRGBA {
 <35FF44E0-6C7C-11cf-8F52-0040333594A3>
 FLOAT red;
 FLOAT green;
 FLOAT blue;
 FLOAT alpha;
}

template ColorRGB {
 <D3E16E81-7835-11cf-8F52-0040333594A3>
 FLOAT red;
 FLOAT green;
 FLOAT blue;
}

template IndexedColor {
 <1630B820-7842-11cf-8F52-0040333594A3>
 DWORD index;
 ColorRGBA indexColor;
}

template Boolean {
 <4885AE61-78E8-11cf-8F52-0040333594A3>
 WORD truefalse;
}

template Boolean2d {
 <4885AE63-78E8-11cf-8F52-0040333594A3>
 Boolean u;
 Boolean v;
}

template MaterialWrap {
 <4885AE60-78E8-11cf-8F52-0040333594A3>
 Boolean u;
 Boolean v;
}

template TextureFilename {
 <A42790E1-7810-11cf-8F52-0040333594A3>
 STRING filename;
}

template Material {
 <3D82AB4D-62DA-11cf-AB39-0020AF71E433>
 ColorRGBA faceColor;
 FLOAT power;
 ColorRGB specularColor;
 ColorRGB emissiveColor;
 [...]
}

template MeshFace {
 <3D82AB5F-62DA-11cf-AB39-0020AF71E433>
 DWORD nFaceVertexIndices;
 array DWORD faceVertexIndices[nFaceVertexIndices];
}

template MeshFaceWraps {
 <4885AE62-78E8-11cf-8F52-0040333594A3>
 DWORD nFaceWrapValues;
 Boolean2d faceWrapValues;
}

template MeshTextureCoords {
 <F6F23F40-7686-11cf-8F52-0040333594A3>
 DWORD nTextureCoords;
 array Coords2d textureCoords[nTextureCoords];
}

template MeshMaterialList {
 <F6F23F42-7686-11cf-8F52-0040333594A3>
 DWORD nMaterials;
 DWORD nFaceIndexes;
 array DWORD faceIndexes[nFaceIndexes];
 [Material]
}

template MeshNormals {
 <F6F23F43-7686-11cf-8F52-0040333594A3>
 DWORD nNormals;
 array Vector normals[nNormals];
 DWORD nFaceNormals;
 array MeshFace faceNormals[nFaceNormals];
}

template MeshVertexColors {
 <1630B821-7842-11cf-8F52-0040333594A3>
 DWORD nVertexColors;
 array IndexedColor vertexColors[nVertexColors];
}

template Mesh {
 <3D82AB44-62DA-11cf-AB39-0020AF71E433>
 DWORD nVertices;
 array Vector vertices[nVertices];
 DWORD nFaces;
 array MeshFace faces[nFaces];
 [...]
}

template FrameTransformMatrix {
 <F6F23F41-7686-11cf-8F52-0040333594A3>
 Matrix4x4 frameMatrix;
}

template Frame {
 <3D82AB46-62DA-11cf-AB39-0020AF71E433>
 [...]
}

Header {
	1; // Major version
	0; // Minor version
	1; // Flags
}

Material xof_default_4 {
	0.400000;0.400000;0.400000;1.000000;;
	32.000000;
	0.700000;0.700000;0.700000;;
	0.000000;0.000000;0.000000;;
}

Material Tyre_Black_3 {
	0.031373;0.031373;0.031373;1.000000;;
	41.000000;
	0.363569;0.363569;0.363569;;
	0.000000;0.000000;0.000000;;
}

// Top-most frame encompassing the 'World'
Frame Frame_World {
	FrameTransformMatrix {
		1.000000, 0.0, 0.0, 0.0, 
		0.0, 1.000000, 0.0, 0.0, 
		0.0, 0.0, -1.000000, 0.0, 
		0.0, 0.0, 0.0, 1.000000;;
	}

Frame Frame_Wheel_F_L_1 {
	FrameTransformMatrix {
		1.000000, 0.0, 0.0, 0.0, 
		0.0, 1.000000, 0.0, 0.0, 
		0.0, 0.0, 1.000000, 0.0, 
		0.0, 0.0, 0.0, 1.000000;;
	}

// Original object name = "Wheel_F_L_1"
Mesh Wheel_F_L_1 {
	13;		// 13 vertices
	-0.119338;0.000000;0.230463;,
	-0.119338;0.115232;0.199587;,
	-0.119338;0.199587;0.115231;,
	-0.119338;0.230463;-0.000000;,
	-0.119338;0.199587;-0.115232;,
	-0.119338;0.115232;-0.199587;,
	-0.119338;-0.000000;-0.230463;,
	-0.119338;-0.115232;-0.199587;,
	-0.119338;-0.199587;-0.115231;,
	-0.119338;-0.230463;0.000000;,
	-0.119338;-0.199587;0.115232;,
	-0.119338;-0.115232;0.199587;,
	-0.119338;0.000000;-0.000000;;

	12;		// 12 faces
	3;1,0,12;,
	3;2,1,12;,
	3;3,2,12;,
	3;4,3,12;,
	3;5,4,12;,
	3;6,5,12;,
	3;7,6,12;,
	3;8,7,12;,
	3;9,8,12;,
	3;10,9,12;,
	3;11,10,12;,
	3;0,11,12;;

	MeshMaterialList {
		1;1;0;;
		{Tyre_Black_3}
	}

	MeshNormals {
		1; // 1 normals
		-1.000000;-0.000000;-0.000000;;

		12;		// 12 faces
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;;
	}  // End of Normals
} // End of Mesh
} // End of frame for 'Wheel_F_L_1'

Frame Frame_Wheel_F_L_2 {
	FrameTransformMatrix {
		1.000000, 0.0, 0.0, 0.0, 
		0.0, 1.000000, 0.0, 0.0, 
		0.0, 0.0, 1.000000, 0.0, 
		0.0, 0.0, 0.0, 1.000000;;
	}

// Original object name = "Wheel_F_L_2"
Mesh Wheel_F_L_2 {
	24;		// 24 vertices
	0.119338;0.000000;0.230463;,
	0.119338;0.115232;0.199587;,
	0.119338;0.199587;0.115231;,
	0.119338;0.230463;-0.000000;,
	0.119338;0.199587;-0.115232;,
	0.119338;0.115232;-0.199587;,
	0.119338;-0.000000;-0.230463;,
	0.119338;-0.115232;-0.199587;,
	0.119338;-0.199587;-0.115231;,
	0.119338;-0.230463;0.000000;,
	0.119338;-0.199587;0.115232;,
	0.119338;-0.115232;0.199587;,
	-0.119338;0.000000;0.230463;,
	-0.119338;0.115232;0.199587;,
	-0.119338;0.199587;0.115232;,
	-0.119338;0.230463;-0.000000;,
	-0.119338;0.199587;-0.115232;,
	-0.119338;0.115232;-0.199587;,
	-0.119338;-0.000000;-0.230463;,
	-0.119338;-0.115232;-0.199587;,
	-0.119338;-0.199587;-0.115231;,
	-0.119338;-0.230463;0.000000;,
	-0.119338;-0.199587;0.115232;,
	-0.119338;-0.115232;0.199587;;

	24;		// 24 faces
	3;12,13,0;,
	3;13,1,0;,
	3;13,14,1;,
	3;14,2,1;,
	3;14,15,2;,
	3;15,3,2;,
	3;15,16,3;,
	3;16,4,3;,
	3;16,17,4;,
	3;17,5,4;,
	3;17,18,5;,
	3;18,6,5;,
	3;18,19,6;,
	3;19,7,6;,
	3;19,20,7;,
	3;20,8,7;,
	3;20,21,8;,
	3;21,9,8;,
	3;21,22,9;,
	3;22,10,9;,
	3;22,23,10;,
	3;23,11,10;,
	3;23,12,11;,
	3;12,0,11;;

	MeshMaterialList {
		1;1;0;;
		{Tyre_Black_3}
	}

	MeshNormals {
		24; // 24 normals
		-0.000000;0.420974;-0.907073;,
		-0.000000;0.088962;-0.996035;,
		-0.000000;0.575061;-0.818111;,
		-0.000000;-0.088962;-0.996035;,
		-0.000000;0.818110;-0.575061;,
		-0.000000;-0.420974;-0.907073;,
		-0.000000;0.907073;-0.420974;,
		-0.000000;-0.575061;-0.818111;,
		-0.000000;0.996035;-0.088962;,
		-0.000000;-0.818110;-0.575061;,
		-0.000000;0.996035;0.088962;,
		-0.000000;-0.907073;-0.420974;,
		0.000000;0.907073;0.420974;,
		0.000000;-0.996035;-0.088962;,
		0.000000;0.818110;0.575061;,
		0.000000;-0.996035;0.088963;,
		0.000000;0.575061;0.818111;,
		0.000000;-0.907073;0.420974;,
		0.000000;0.420974;0.907073;,
		0.000000;-0.818110;0.575061;,
		0.000000;0.088962;0.996035;,
		0.000000;-0.575061;0.818111;,
		0.000000;-0.088962;0.996035;,
		0.000000;-0.420974;0.907073;;

		24;		// 24 faces
		3;22,18,20;,
		3;18,16,20;,
		3;18,14,16;,
		3;14,12,16;,
		3;14,10,12;,
		3;10,8,12;,
		3;10,6,8;,
		3;6,4,8;,
		3;6,2,4;,
		3;2,0,4;,
		3;2,1,0;,
		3;1,3,0;,
		3;1,5,3;,
		3;5,7,3;,
		3;5,9,7;,
		3;9,11,7;,
		3;9,13,11;,
		3;13,15,11;,
		3;13,17,15;,
		3;17,19,15;,
		3;17,21,19;,
		3;21,23,19;,
		3;21,22,23;,
		3;22,20,23;;
	}  // End of Normals
} // End of Mesh
} // End of frame for 'Wheel_F_L_2'

Frame Frame_Wheel_F_L_3 {
	FrameTransformMatrix {
		1.000000, 0.0, 0.0, 0.0, 
		0.0, 1.000000, 0.0, 0.0, 
		0.0, 0.0, 1.000000, 0.0, 
		0.0, 0.0, 0.0, 1.000000;;
	}

// Original object name = "Wheel_F_L_3"
Mesh Wheel_F_L_3 {
	13;		// 13 vertices
	0.119338;0.000000;0.000000;,
	0.119338;0.000000;0.230463;,
	0.119338;0.115232;0.199587;,
	0.119338;0.199587;0.115231;,
	0.119338;0.230463;-0.000000;,
	0.119338;0.199587;-0.115232;,
	0.119338;0.115232;-0.199587;,
	0.119338;-0.000000;-0.230463;,
	0.119338;-0.115232;-0.199587;,
	0.119338;-0.199587;-0.115231;,
	0.119338;-0.230463;0.000000;,
	0.119338;-0.199587;0.115232;,
	0.119338;-0.115232;0.199587;;

	12;		// 12 faces
	3;1,2,0;,
	3;2,3,0;,
	3;3,4,0;,
	3;4,5,0;,
	3;5,6,0;,
	3;6,7,0;,
	3;7,8,0;,
	3;8,9,0;,
	3;9,10,0;,
	3;10,11,0;,
	3;11,12,0;,
	3;12,1,0;;

	MeshMaterialList {
		1;1;0;;
		{Tyre_Black_3}
	}

	MeshNormals {
		1; // 1 normals
		1.000000;0.000000;0.000000;;

		12;		// 12 faces
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;,
		3;0,0,0;;
	}  // End of Normals
} // End of Mesh
} // End of frame for 'Wheel_F_L_3'
} // End of "World" frame

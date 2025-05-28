CREATE TABLE "Chapter" (
    "Name" TEXT,
    "ID" TEXT,
    "structure name" TEXT,
    "item name" TEXT,
    PRIMARY KEY ("ID")
);
CREATE TABLE "Item" (
    "Name" TEXT,
    "ID" TEXT,
    "StructureLookup" TEXT,
    PRIMARY KEY ("ID")
);
CREATE TABLE "Structure" (
    "Name" TEXT,
    "ID" TEXT,
    "type" TEXT,
    "notes" TEXT,
    PRIMARY KEY ("ID")
);
-- Foreign Key Constraints
ALTER TABLE "Chapter"
ADD CONSTRAINT "fk_Chapter_item name" FOREIGN KEY ("item name")
REFERENCES "Item" ("ID");
ALTER TABLE "Chapter"
ADD CONSTRAINT "fk_Chapter_structure name" FOREIGN KEY ("structure name")
REFERENCES "Structure" ("ID");
ALTER TABLE "Item"
ADD CONSTRAINT "fk_Item_StructureLookup" FOREIGN KEY ("StructureLookup")
REFERENCES "Structure" ("ID");
ALTER TABLE "Structure"
ADD CONSTRAINT "fk_Structure_notes" FOREIGN KEY ("notes")
REFERENCES "Chapter" ("ID");
